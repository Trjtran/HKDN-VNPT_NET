import argparse
import json
import random
import socket
import time
from datetime import datetime

FACILITY = 4  # security/authorization

INTERNAL_IPS = [f"10.10.{i}.{j}" for i in range(1, 6) for j in (10, 20, 25, 50, 100)]
EXTERNAL_IPS = ["8.8.8.8", "1.1.1.1", "208.67.222.222"]
ATTACKER_IPS = ["185.220.101.4", "45.155.205.233", "91.134.202.160", "103.21.244.10"]

NORMAL_PORTS = [53, 80, 443, 8080]
RISK_PORTS = [22, 23, 445, 3389]

# Định nghĩa từng sự kiện (event) theo đặc trưng Cisco ASA
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

NORMAL_EVENTS = ["connection_built", "connection_teardown", "acl_permitted"]
ALERT_EVENTS = ["firewall_deny", "icmp_sweep", "vpn_tunnel_down"]


def build_event_payload(force_alert: bool = False) -> dict:
    event_name = random.choice(ALERT_EVENTS if force_alert else NORMAL_EVENTS)
    meta = EVENT_TEMPLATES[event_name]

    # Giao thức (proto)
    if event_name == "icmp_sweep":
        proto = "ICMP"
    elif event_name == "acl_permitted":
        proto = random.choice(["TCP", "UDP"])
    elif event_name == "firewall_deny":
        proto = random.choice(["TCP", "UDP"])
    else:
        proto = meta["default_proto"]

    # IP nguồn, IP đích (dst_ip) và Port (src_port, dst_port)
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
    else:  # vpn_tunnel_down
        src_ip = random.choice(ATTACKER_IPS[:2])
        dst_ip = random.choice(INTERNAL_IPS[:3])
        src_port = 500
        dst_port = 4500

    now_dt = datetime.now()
    return {
        "timestamp_iso": now_dt.isoformat(timespec="seconds"),
        "syslog_time": now_dt.strftime("%b %d %H:%M:%S"),
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


def render_log(data: dict, hostname: str, output_format: str) -> str:
    if output_format == "json":
        return json.dumps({"hostname": hostname, **data}, ensure_ascii=False)

    pri = FACILITY * 8 + data["sev_code"]
    asa_code = f"%ASA-{data['sev_code']}-{data['asa_id']}"
    conn_id = random.randint(100000, 999999)

    ev = data["event"]
    if ev == "connection_built":
        asa_msg = (
            f"Built outbound {data['proto']} connection {conn_id} "
            f"for outside:{data['dst_ip']}/{data['dst_port']} to inside:{data['src_ip']}/{data['src_port']}"
        )
    elif ev == "connection_teardown":
        asa_msg = (
            f"Teardown {data['proto']} connection {conn_id} "
            f"for outside:{data['dst_ip']}/{data['dst_port']} to inside:{data['src_ip']}/{data['src_port']}"
        )
    elif ev == "acl_permitted":
        asa_msg = (
            f"{data['proto']} access permitted by ACL from "
            f"inside:{data['src_ip']}/{data['src_port']} to outside:{data['dst_ip']}/{data['dst_port']}"
        )
    elif ev == "firewall_deny":
        asa_msg = (
            f"Deny {data['proto'].lower()} src outside:{data['src_ip']}/{data['src_port']} "
            f"dst inside:{data['dst_ip']}/{data['dst_port']} by access-group \"OUTSIDE_IN\""
        )
    elif ev == "icmp_sweep":
        asa_msg = f"IDS:2001 ICMP Sweep from {data['src_ip']} to {data['dst_ip']} on interface outside"
    else:  # vpn_tunnel_down
        asa_msg = (
            f"Group = RemoteVPN, IP = {data['src_ip']} -> {data['dst_ip']}:{data['dst_port']}, "
            f"Tunnel has been torn down. Reason: Peer Disconnected"
        )

    # Gắn rõ các trường cốt lõi ở cuối để Logstash kv/grok bắt nhanh
    fields_tail = (
        f"event={data['event']} action={data['action']} severity={data['severity']} "
        f"proto={data['proto']} src_ip={data['src_ip']} src_port={data['src_port']} "
        f"dst_ip={data['dst_ip']} dst_port={data['dst_port']}"
    )
    return f"<{pri}>{data['syslog_time']} {hostname} : {asa_code}: {asa_msg} | {fields_tail}"


def main():
    parser = argparse.ArgumentParser(description="Cisco Firewall Log Generator cho Logstash")
    parser.add_argument("--host", default="127.0.0.1", help="IP đích nhận log (máy ảo/host chạy Logstash)")
    parser.add_argument("--port", type=int, default=5514, help="Port UDP nhận log")
    parser.add_argument("--hostname", default="ASA-EDGE-01", help="Hostname thiết bị Firewall")
    parser.add_argument("--format", choices=["syslog", "json"], default="syslog", help="Định dạng log xuất ra")
    parser.add_argument("--interval", type=float, default=0.5, help="Khoảng nghỉ giữa các gói log (giây)")
    parser.add_argument("--burst-every", type=int, default=10, help="Cứ N nhịp thì sinh đợt sự kiện cảnh báo (0 = tắt)")
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(
        f"Gửi log [{args.format}] -> {args.host}:{args.port} | "
        f"interval={args.interval}s | burst_every={args.burst_every}"
    )

    step = 0
    try:
        while True:
            step += 1
            is_alert = args.burst_every > 0 and (step % args.burst_every) in (1, 2, 3)
            payload = build_event_payload(force_alert=is_alert)
            line = render_log(payload, args.hostname, args.format)
            sock.sendto(line.encode("utf-8"), (args.host, args.port))
            print(line)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nĐã dừng gửi log.")
    finally:
        sock.close()


if __name__ == "__main__":
    main()