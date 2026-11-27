"""Synthetic Cisco-ASA-style firewall Syslog generator.

The generator emits lab data only. Event IDs and message bodies should be
validated against the exact ASA software/version before being described as
vendor-authentic. The default Syslog format matches the companion firewall.conf.
"""

import argparse
import json
import random
import socket
import time
from datetime import datetime, timezone

FACILITY = 4  # security/authorization

INTERNAL_IPS = [
    f"10.10.{i}.{j}"
    for i in range(1, 6)
    for j in (10, 20, 25, 50, 100)
]
EXTERNAL_IPS = ["8.8.8.8", "1.1.1.1", "208.67.222.222"]
ATTACKER_IPS = [
    "185.220.101.4",
    "45.155.205.233",
    "91.134.202.160",
    "103.21.244.10",
]

NORMAL_PORTS = [53, 80, 443, 8080]
RISK_PORTS = [22, 23, 445, 3389]

# Message IDs are retained from the team's initial simulation.
# Confirm them against the target ASA release before claiming authenticity.
EVENT_TEMPLATES = {
    "connection_built": {
        "sev_code": 6,
        "severity": "informational",
        "asa_id": "302013",
        "action": "allow",
        "default_proto": "TCP",
    },
    "connection_teardown": {
        "sev_code": 6,
        "severity": "informational",
        "asa_id": "302014",
        "action": "allow",
        "default_proto": "TCP",
    },
    "acl_permitted": {
        "sev_code": 5,
        "severity": "notification",
        "asa_id": "710003",
        "action": "allow",
        "default_proto": "UDP",
    },
    "firewall_deny": {
        "sev_code": 4,
        "severity": "warning",
        "asa_id": "106023",
        "action": "deny",
        "default_proto": "TCP",
    },
    "icmp_sweep": {
        "sev_code": 2,
        "severity": "critical",
        "asa_id": "400014",
        "action": "drop",
        "default_proto": "ICMP",
    },
    "vpn_tunnel_down": {
        "sev_code": 3,
        "severity": "error",
        "asa_id": "713902",
        "action": "disconnect",
        "default_proto": "UDP",
    },
}

NORMAL_EVENTS = [
    "connection_built",
    "connection_teardown",
    "acl_permitted",
]
ALERT_EVENTS = [
    "firewall_deny",
    "icmp_sweep",
    "vpn_tunnel_down",
]


def _timestamp_fields():
    """Return local Syslog time plus an offset-aware ISO-8601 timestamp."""
    now = datetime.now().astimezone()
    return {
        # Keep this field compatible with the current firewall.conf Grok pattern.
        "syslog_time": now.strftime("%b %d %H:%M:%S"),
        "timestamp_iso": now.isoformat(timespec="milliseconds"),
    }


def build_event_payload(force_alert=False, event_name=None):
    """Build one normalized event payload.

    event_name is optional and primarily useful for deterministic tests.
    """
    if event_name is None:
        event_name = random.choice(ALERT_EVENTS if force_alert else NORMAL_EVENTS)

    if event_name not in EVENT_TEMPLATES:
        raise ValueError(f"Unsupported firewall event: {event_name}")

    meta = EVENT_TEMPLATES[event_name]

    if event_name == "icmp_sweep":
        proto = "ICMP"
    elif event_name in ("acl_permitted", "firewall_deny"):
        proto = random.choice(["TCP", "UDP"])
    else:
        proto = meta["default_proto"]

    if event_name in ("connection_built", "connection_teardown", "acl_permitted"):
        src_ip = random.choice(INTERNAL_IPS)
        dst_ip = random.choice(EXTERNAL_IPS)
        src_port = random.randint(49152, 65535) if proto != "ICMP" else None
        dst_port = random.choice(NORMAL_PORTS) if proto != "ICMP" else None
    elif event_name == "firewall_deny":
        src_ip = random.choice(ATTACKER_IPS)
        dst_ip = random.choice(INTERNAL_IPS)
        src_port = random.randint(1024, 65535) if proto != "ICMP" else None
        dst_port = random.choice(RISK_PORTS) if proto != "ICMP" else None
    elif event_name == "icmp_sweep":
        src_ip = random.choice(ATTACKER_IPS)
        dst_ip = random.choice(INTERNAL_IPS)
        src_port = None
        dst_port = None
    else:
        src_ip = random.choice(ATTACKER_IPS[:2])
        dst_ip = random.choice(INTERNAL_IPS[:3])
        src_port = 500
        dst_port = 4500

    return {
        **_timestamp_fields(),
        "vendor": "cisco_asa",
        "event": event_name,
        "action": meta["action"],
        "severity": meta["severity"],
        "sev_code": meta["sev_code"],
        "asa_id": meta["asa_id"],
        "proto": proto,
        "src_ip": src_ip,
        "src_port": src_port if src_port is not None else "N/A",
        "dst_ip": dst_ip,
        "dst_port": dst_port if dst_port is not None else "N/A",
    }


def _render_asa_message(data):
    """Render the human-readable portion of the simulated ASA event."""
    event = data["event"]

    if event == "connection_built":
        conn_id = random.randint(100000, 999999)
        return (
            f"Built outbound {data['proto']} connection {conn_id} "
            f"for outside:{data['dst_ip']}/{data['dst_port']} "
            f"to inside:{data['src_ip']}/{data['src_port']}"
        )

    if event == "connection_teardown":
        conn_id = random.randint(100000, 999999)
        return (
            f"Teardown {data['proto']} connection {conn_id} "
            f"for outside:{data['dst_ip']}/{data['dst_port']} "
            f"to inside:{data['src_ip']}/{data['src_port']}"
        )

    if event == "acl_permitted":
        return (
            f"{data['proto']} access permitted by ACL from "
            f"inside:{data['src_ip']}/{data['src_port']} "
            f"to outside:{data['dst_ip']}/{data['dst_port']}"
        )

    if event == "firewall_deny":
        return (
            f"Deny {data['proto'].lower()} src outside:"
            f"{data['src_ip']}/{data['src_port']} dst inside:"
            f"{data['dst_ip']}/{data['dst_port']} "
            'by access-group "OUTSIDE_IN"'
        )

    if event == "icmp_sweep":
        return (
            f"IDS:2001 ICMP Sweep from {data['src_ip']} "
            f"to {data['dst_ip']} on interface outside"
        )

    return (
        f"Group = RemoteVPN, IP = {data['src_ip']} -> "
        f"{data['dst_ip']}:{data['dst_port']}, "
        "Tunnel has been torn down. Reason: Peer Disconnected"
    )


def render_log(data, hostname, output_format):
    """Render JSON or Syslog; Syslog is the integration default."""
    if output_format == "json":
        return json.dumps(
            {"hostname": hostname, **data},
            ensure_ascii=False
        )

    pri = FACILITY * 8 + data["sev_code"]
    asa_code = f"%ASA-{data['sev_code']}-{data['asa_id']}"
    asa_message = _render_asa_message(data)

    # Keep the key=value tail simple for the existing Logstash kv filter.
    fields_tail = (
        f"event={data['event']} action={data['action']} "
        f"severity={data['severity']} proto={data['proto']} "
        f"src_ip={data['src_ip']} src_port={data['src_port']} "
        f"dst_ip={data['dst_ip']} dst_port={data['dst_port']}"
    )
    return (
        f"<{pri}>{data['syslog_time']} {hostname} : "
        f"{asa_code}: {asa_message} | {fields_tail}"
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Synthetic Firewall Syslog Generator"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Destination IP of the Syslog receiver"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5514,
        help="UDP destination port"
    )
    parser.add_argument(
        "--hostname",
        default="ASA-EDGE-01",
        help="Simulated Firewall hostname"
    )
    parser.add_argument(
        "--format",
        choices=["syslog", "json"],
        default="syslog",
        help="Output format; use syslog with the current firewall.conf"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5,
        help="Delay between datagrams in seconds"
    )
    parser.add_argument(
        "--burst-every",
        type=int,
        default=10,
        help="Emit alert events every N ticks; 0 disables alert bursts"
    )
    args = parser.parse_args()

    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    if args.interval < 0:
        parser.error("--interval cannot be negative")
    if args.burst_every < 0:
        parser.error("--burst-every cannot be negative")

    return args


def main():
    args = parse_args()

    if args.format == "json":
        print(
            "[WARNING] JSON output is not parsed by the current "
            "firewall.conf; use --format syslog for the shared pipeline."
        )

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(
        f"Firewall Syslog Generator [{args.format}] -> "
        f"{args.host}:{args.port} | interval={args.interval}s | "
        f"burst_every={args.burst_every}"
    )
    print("Data is synthetic. Press Ctrl+C to stop.")

    step = 0
    try:
        while True:
            step += 1
            is_alert = (
                args.burst_every > 0
                and (step % args.burst_every) in (1, 2, 3)
            )
            payload = build_event_payload(force_alert=is_alert)
            line = render_log(payload, args.hostname, args.format)

            try:
                sock.sendto(
                    line.encode("utf-8"),
                    (args.host, args.port)
                )
                print(f"[SENT] {line}")
            except OSError as error:
                print(f"[SEND ERROR] {error}")

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n[STOP] Firewall Syslog Generator stopped.")
    finally:
        sock.close()
        print("[CLOSED] UDP socket closed.")


if __name__ == "__main__":
    main()
