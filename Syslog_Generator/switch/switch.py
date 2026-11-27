# ============================================================
# SWITCH SYSLOG GENERATOR
# Simulated Switch events with state-aware transitions
# ============================================================

import random
import socket
import time

from . import config


# ============================================================
# DEVICE STATE
# ============================================================

interface_states = {
    interface: "up"
    for interface in config.INTERFACES
}

vlan_states = {
    vlan: "up"
    for vlan in config.VLANS
}

port_security_states = {
    interface: "normal"
    for interface in config.INTERFACES
}

# EtherChannel membership is a lab simulation, not a real device config.
etherchannel_states = {
    1: {
        "members": config.INTERFACES[:2],
        "member_states": {
            interface: "up" for interface in config.INTERFACES[:2]
        }
    },
    2: {
        "members": config.INTERFACES[2:4],
        "member_states": {
            interface: "up" for interface in config.INTERFACES[2:4]
        }
    }
}

login_attempts = {}
LOGIN_FAILURE_THRESHOLD = 5
LOGIN_SOURCE_IPS = ["192.0.2.100", "198.51.100.25"]


# ============================================================
# SYSLOG HELPERS
# ============================================================

def get_timestamp():
    """Return timestamp with milliseconds and local UTC offset."""
    now = time.time()
    timestamp = time.strftime("%b %d %H:%M:%S", time.localtime(now))
    milliseconds = int((now % 1) * 1000)
    timezone_offset = time.strftime("%z")
    return f"{timestamp}.{milliseconds:03d} {timezone_offset}"


def generate_synthetic_syslog(event_type, severity, message):
    """Create a clearly labelled synthetic Switch event."""
    timestamp = get_timestamp()
    return (
        f"{config.NODE_ID}:"
        f"{timestamp}: "
        f"{config.PROCESS_NAME}: "
        f"%SYNTH-{severity}-{event_type.upper()} : "
        f"{message}"
    )


def send_syslog(sock, message):
    """Send one UDP Syslog datagram."""
    try:
        sock.sendto(
            message.encode("utf-8"),
            (config.SYSLOG_SERVER_IP, config.SYSLOG_SERVER_PORT)
        )
        print(f"[SENT] {message}")
    except OSError as error:
        print(f"[ERROR] Cannot send Syslog: {error}")


def emit_event(sock, event_type, severity, message):
    send_syslog(
        sock,
        generate_synthetic_syslog(event_type, severity, message)
    )


def wait_between_events():
    time.sleep(config.LOG_INTERVAL)


def set_interface_state(sock, interface, new_state, reason=None):
    """
    Change an interface state only when it actually changes.
    Returns True when a transition was emitted.
    """
    if interface not in interface_states:
        print(f"[WARNING] Unknown interface: {interface}")
        return False

    if new_state not in ("up", "down", "err-disabled"):
        print(f"[WARNING] Invalid interface state: {new_state}")
        return False

    old_state = interface_states[interface]
    if old_state == new_state:
        return False

    interface_states[interface] = new_state

    event_type = "INTERFACE_DOWN" if new_state != "up" else "INTERFACE_UP"
    severity = 3 if new_state != "up" else 5
    state_text = "Down" if new_state != "up" else "Up"
    detail = f"Interface {interface}, changed state to {state_text}"
    if reason:
        detail += f" ({reason})"

    emit_event(sock, event_type, severity, detail)
    return True


def print_switch_status():
    print("\n[SWITCH INTERFACE STATUS]")
    print("-" * 55)
    for interface, state in interface_states.items():
        print(f"{interface:<24} | {state}")
    print("-" * 55)


# ============================================================
# SCENARIO 1: PORT LINK FAILURE
# ============================================================

def scenario_port_link_failure(sock):
    """Take an active port down and recover it; avoid duplicate transitions."""
    available = [
        interface for interface, state in interface_states.items()
        if state == "up"
    ]

    if not available:
        down_ports = [
            interface for interface, state in interface_states.items()
            if state == "down"
        ]
        if not down_ports:
            print("[INFO] No interface is available for link simulation.")
            return
        interface = random.choice(down_ports)
        set_interface_state(sock, interface, "up", "simulated recovery")
        return

    interface = random.choice(available)
    if set_interface_state(sock, interface, "down", "simulated link failure"):
        wait_between_events()
        set_interface_state(sock, interface, "up", "simulated link recovery")


# ============================================================
# SCENARIO 2: INTERFACE FLAPPING
# ============================================================

def scenario_interface_flapping(sock):
    """Alternate the selected interface state, starting from its real state."""
    interface = random.choice(config.INTERFACES)
    current = interface_states[interface]

    if current == "err-disabled":
        print(f"[INFO] {interface} is err-disabled; skipping flapping.")
        return

    for _ in range(4):
        new_state = "down" if current == "up" else "up"
        set_interface_state(sock, interface, new_state, "simulated flapping")
        current = new_state
        wait_between_events()


# ============================================================
# SCENARIO 3: VLAN FAILURE
# ============================================================

def scenario_vlan_failure(sock):
    vlan = random.choice(config.VLANS)
    if vlan_states[vlan] == "up":
        vlan_states[vlan] = "down"
        emit_event(
            sock, "VLAN_DOWN", 3,
            f"Line protocol on Interface Vlan{vlan}, changed state to Down"
        )
        wait_between_events()
        vlan_states[vlan] = "up"
        emit_event(
            sock, "VLAN_UP", 5,
            f"Line protocol on Interface Vlan{vlan}, changed state to Up"
        )
    else:
        vlan_states[vlan] = "up"
        emit_event(
            sock, "VLAN_UP", 5,
            f"Line protocol on Interface Vlan{vlan}, changed state to Up"
        )


# ============================================================
# SCENARIO 4: MAC FLAPPING
# ============================================================

def scenario_mac_flapping(sock):
    if len(config.INTERFACES) < 2:
        print("[WARNING] At least two interfaces are required for MAC flapping.")
        return

    vlan = random.choice(config.VLANS)
    interfaces = random.sample(config.INTERFACES, 2)
    mac_address = "0011.2233.4455"

    emit_event(
        sock, "MAC_FLAPPING", 4,
        f"Host {mac_address} in VLAN {vlan} is flapping between "
        f"port {interfaces[0]} and port {interfaces[1]}"
    )
    wait_between_events()
    emit_event(
        sock, "MAC_FLAPPING", 4,
        f"MAC address {mac_address} continues moving between "
        f"port {interfaces[0]} and port {interfaces[1]}"
    )


# ============================================================
# SCENARIO 5: PORT SECURITY
# ============================================================

def scenario_port_security_violation(sock):
    available = [
        interface for interface in config.INTERFACES
        if port_security_states[interface] == "normal"
        and interface_states[interface] == "up"
    ]
    if not available:
        print("[INFO] No active interface available for Port Security test.")
        return

    interface = random.choice(available)
    mac_address = "00AA.BBCC.DDEE"

    port_security_states[interface] = "violation"
    set_interface_state(
        sock, interface, "err-disabled",
        "Port Security violation"
    )
    emit_event(
        sock, "PORT_SECURITY_VIOLATION", 2,
        f"Security violation detected on interface {interface}, "
        f"MAC address {mac_address}"
    )

    wait_between_events()

    # This scenario owns the err-disabled transition and restores only this port.
    if interface_states[interface] == "err-disabled":
        set_interface_state(
            sock, interface, "up",
            "simulated administrator recovery"
        )
    port_security_states[interface] = "normal"
    emit_event(
        sock, "PORT_SECURITY_RECOVERED", 5,
        f"Simulated Port Security recovery on interface {interface}"
    )


# ============================================================
# SCENARIO 6: DHCP SNOOPING
# ============================================================

def scenario_dhcp_snooping_violation(sock):
    interface = random.choice(config.INTERFACES)
    vlan = random.choice(config.VLANS)

    emit_event(
        sock, "DHCP_SNOOPING_VIOLATION", 4,
        f"Unauthorized DHCP server detected on interface {interface}, VLAN {vlan}"
    )
    wait_between_events()
    emit_event(
        sock, "DHCP_SNOOPING_BLOCKED", 5,
        f"DHCP response from unauthorized server on interface {interface} was blocked"
    )


# ============================================================
# SCENARIO 7: UNAUTHORIZED LOGIN
# ============================================================

def scenario_unauthorized_login(sock):
    """Count failed logins per source IP across scenario invocations."""
    source_ip = random.choice(LOGIN_SOURCE_IPS)
    login_attempts[source_ip] = login_attempts.get(source_ip, 0) + 1
    attempts = login_attempts[source_ip]

    emit_event(
        sock, "LOGIN_FAILED", 4,
        f"Login failed from {source_ip}, consecutive attempts: {attempts}"
    )

    if attempts >= LOGIN_FAILURE_THRESHOLD:
        emit_event(
            sock, "LOGIN_THRESHOLD", 2,
            f"Security alert: {attempts} failed login attempts detected "
            f"from {source_ip}"
        )
        login_attempts[source_ip] = 0


# ============================================================
# SCENARIO 8: STP TOPOLOGY CHANGE
# ============================================================

def scenario_stp_topology_change(sock):
    vlan = random.choice(config.VLANS)
    emit_event(
        sock, "STP_TOPOLOGY_CHANGE", 2,
        f"Topology change detected in VLAN {vlan}"
    )
    wait_between_events()
    emit_event(
        sock, "STP_TOPOLOGY_STABLE", 5,
        f"STP topology in VLAN {vlan} is stable"
    )


# ============================================================
# SCENARIO 9: ETHERCHANNEL MEMBER FAILURE
# ============================================================

def scenario_etherchannel_failure(sock):
    available_groups = [
        group_id for group_id, group in etherchannel_states.items()
        if any(
            group["member_states"][member] == "up"
            and interface_states.get(member) == "up"
            for member in group["members"]
        )
    ]
    if not available_groups:
        print("[INFO] No active EtherChannel member available.")
        return

    group_id = random.choice(available_groups)
    group = etherchannel_states[group_id]
    active_members = [
        member for member in group["members"]
        if group["member_states"][member] == "up"
        and interface_states.get(member) == "up"
    ]
    interface = random.choice(active_members)

    group["member_states"][interface] = "down"
    set_interface_state(
        sock, interface, "down",
        f"EtherChannel group {group_id} member failure"
    )

    remaining = sum(
        1 for member in group["members"]
        if group["member_states"][member] == "up"
        and interface_states.get(member) == "up"
    )
    emit_event(
        sock, "ETHERCHANNEL_MEMBER_DOWN", 3,
        f"EtherChannel group {group_id}: member {interface} is down, "
        f"remaining active members: {remaining}"
    )

    wait_between_events()

    group["member_states"][interface] = "up"
    set_interface_state(
        sock, interface, "up",
        f"EtherChannel group {group_id} member recovered"
    )
    emit_event(
        sock, "ETHERCHANNEL_MEMBER_RECOVERED", 5,
        f"EtherChannel group {group_id}: member {interface} has been recovered"
    )


# ============================================================
# SCENARIO 10: CONFIGURATION CHANGE
# ============================================================

def scenario_configuration_change(sock):
    source_ip = "192.0.2.10"
    emit_event(
        sock, "CONFIGURATION_CHANGE", 5,
        f"Configuration changed by simulated admin from {source_ip}"
    )


SCENARIOS = [
    ("Port Link Failure", scenario_port_link_failure),
    ("Interface Flapping", scenario_interface_flapping),
    ("VLAN Failure", scenario_vlan_failure),
    ("MAC Flapping", scenario_mac_flapping),
    ("Port Security Violation", scenario_port_security_violation),
    ("DHCP Snooping Violation", scenario_dhcp_snooping_violation),
    ("Unauthorized Login", scenario_unauthorized_login),
    ("STP Topology Change", scenario_stp_topology_change),
    ("EtherChannel Failure", scenario_etherchannel_failure),
    ("Configuration Change", scenario_configuration_change)
]


def simulate_switch_event(sock):
    scenario_name, scenario_function = random.choice(SCENARIOS)
    print(f"\n[SCENARIO] {scenario_name}")
    scenario_function(sock)
    print_switch_status()


def start_switch_generator():
    print("=" * 55)
    print("SWITCH SYSLOG GENERATOR")
    print("=" * 55)
    print(f"Switch name   : {config.SWITCH_NAME}")
    print(f"Switch IP     : {config.SWITCH_IP}")
    print(f"Syslog server : {config.SYSLOG_SERVER_IP}:{config.SYSLOG_SERVER_PORT}")
    print(f"Protocol      : {config.SYSLOG_PROTOCOL}")
    print(f"Process       : {config.PROCESS_NAME}")
    print(f"Total scenarios: {len(SCENARIOS)}")
    print("SYNTH-* event codes are simulated, not vendor-native IDs.")
    print("Press Ctrl+C to stop the generator.")
    print("=" * 55)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        while True:
            simulate_switch_event(sock)
            time.sleep(config.SCENARIO_INTERVAL)
    except KeyboardInterrupt:
        print("\n[STOP] Switch Syslog Generator stopped.")
    finally:
        sock.close()
        print("[CLOSED] UDP socket closed.")


if __name__ == "__main__":
    start_switch_generator()
