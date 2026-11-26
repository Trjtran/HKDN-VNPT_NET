# ============================================================
# SWITCH SYSLOG GENERATOR
# Mô phỏng các sự kiện và cảnh báo trên thiết bị Switch
# ============================================================

import random
import socket
import time

from . import config


# ============================================================
# 1. KHỞI TẠO VÀ THEO DÕI TRẠNG THÁI SWITCH
# ============================================================

# Theo dõi trạng thái của từng cổng mạng
interface_states = {
    interface: "up"
    for interface in config.INTERFACES
}

# Theo dõi trạng thái của từng VLAN
vlan_states = {
    vlan: "up"
    for vlan in config.VLANS
}

# Theo dõi trạng thái bảo mật của từng cổng
port_security_states = {
    interface: "normal"
    for interface in config.INTERFACES
}

# Mô phỏng hai nhóm EtherChannel
# Nhóm 1 gồm hai cổng đầu tiên, nhóm 2 gồm các cổng còn lại.
# Đây là cấu hình mô phỏng, không phải cấu hình của Switch thực tế.
etherchannel_states = {
    1: {
        "members": config.INTERFACES[:2],
        "member_states": {
            interface: "up"
            for interface in config.INTERFACES[:2]
        }
    },
    2: {
        "members": config.INTERFACES[2:4],
        "member_states": {
            interface: "up"
            for interface in config.INTERFACES[2:4]
        }
    }
}

# Theo dõi số lần đăng nhập thất bại theo địa chỉ IP
login_attempts = {}


# ============================================================
# 2. CÁC HÀM XỬ LÝ SYSLOG
# ============================================================

def get_timestamp():
    """Tạo timestamp có mili giây và múi giờ giống cấu trúc Router."""
    now = time.localtime()
    timestamp = time.strftime("%b %d %H:%M:%S", now)
    milliseconds = int((time.time() % 1) * 1000)
    timezone_offset = time.strftime("%z")

    return f"{timestamp}.{milliseconds:03d} {timezone_offset}"


def generate_synthetic_syslog(event_type, severity, message):
    """
    Tạo Syslog theo cấu trúc mô phỏng thống nhất của nhóm.

    Lưu ý: SYNTH là mã sự kiện do nhóm quy ước cho chương trình mô phỏng,
    không phải mã Syslog nguyên bản của Cisco Catalyst.
    """
    timestamp = get_timestamp()

    return (
        f"{config.NODE_ID}:"
        f"{timestamp}: "
        f"{config.PROCESS_NAME}: "
        f"%SYNTH-{severity}-{event_type.upper()} : "
        f"{message}"
    )


def send_syslog(sock, message):
    """Gửi Syslog đến máy chủ nhận thông qua giao thức UDP."""
    try:
        sock.sendto(
            message.encode("utf-8"),
            (config.SYSLOG_SERVER_IP, config.SYSLOG_SERVER_PORT)
        )
        print(f"[SENT] {message}")

    except OSError as error:
        print(f"[ERROR] Cannot send Syslog: {error}")


def emit_event(sock, event_type, severity, message):
    """Tạo và gửi một sự kiện Syslog theo định dạng chung."""
    syslog_message = generate_synthetic_syslog(
        event_type,
        severity,
        message
    )
    send_syslog(sock, syslog_message)


def wait_between_events():
    """Tạm dừng giữa các sự kiện trong cùng một kịch bản."""
    time.sleep(config.LOG_INTERVAL)


# ============================================================
# 3. CÁC KỊCH BẢN MÔ PHỎNG SỰ CỐ SWITCH
# ============================================================

# ------------------------------------------------------------
# Kịch bản 1: Cổng mạng bị mất kết nối
# ------------------------------------------------------------

def scenario_port_link_failure(sock):
    """Mô phỏng một cổng mạng chuyển từ UP sang DOWN rồi phục hồi."""

    interface = random.choice(config.INTERFACES)

    # Mô phỏng cổng mạng bị mất kết nối
    interface_states[interface] = "down"

    emit_event(
        sock,
        "INTERFACE_DOWN",
        3,
        f"Interface {interface}, changed state to Down"
    )

    wait_between_events()

    # Mô phỏng cổng mạng hoạt động trở lại
    interface_states[interface] = "up"

    emit_event(
        sock,
        "INTERFACE_UP",
        5,
        f"Interface {interface}, changed state to Up"
    )


# ------------------------------------------------------------
# Kịch bản 2: Cổng mạng liên tục mất và khôi phục kết nối
# ------------------------------------------------------------

def scenario_interface_flapping(sock):
    """Mô phỏng hiện tượng Interface Flapping."""

    interface = random.choice(config.INTERFACES)

    # Thực hiện liên tiếp các lần mất và khôi phục kết nối
    states = ["down", "up", "down", "up"]

    for state in states:
        interface_states[interface] = state

        if state == "down":
            event_type = "INTERFACE_DOWN"
            severity = 3
            display_state = "Down"
        else:
            event_type = "INTERFACE_UP"
            severity = 5
            display_state = "Up"

        emit_event(
            sock,
            event_type,
            severity,
            f"Interface {interface}, changed state to {display_state}"
        )

        wait_between_events()


# ------------------------------------------------------------
# Kịch bản 3: VLAN bị gián đoạn
# ------------------------------------------------------------

def scenario_vlan_failure(sock):
    """Mô phỏng VLAN bị gián đoạn và được khôi phục."""

    vlan = random.choice(config.VLANS)

    # Mô phỏng VLAN bị gián đoạn
    vlan_states[vlan] = "down"

    emit_event(
        sock,
        "VLAN_DOWN",
        3,
        f"Line protocol on Interface Vlan{vlan}, changed state to Down"
    )

    wait_between_events()

    # Mô phỏng VLAN hoạt động trở lại
    vlan_states[vlan] = "up"

    emit_event(
        sock,
        "VLAN_UP",
        5,
        f"Line protocol on Interface Vlan{vlan}, changed state to Up"
    )


# ------------------------------------------------------------
# Kịch bản 4: Địa chỉ MAC bị di chuyển giữa các cổng
# ------------------------------------------------------------

def scenario_mac_flapping(sock):
    """Mô phỏng hiện tượng MAC Flapping."""

    vlan = random.choice(config.VLANS)

    # Chọn hai cổng khác nhau để mô phỏng MAC di chuyển
    interfaces = random.sample(config.INTERFACES, 2)

    interface_1 = interfaces[0]
    interface_2 = interfaces[1]

    mac_address = "0011.2233.4455"

    emit_event(
        sock,
        "MAC_FLAPPING",
        4,
        f"Host {mac_address} in VLAN {vlan} is flapping between "
        f"port {interface_1} and port {interface_2}"
    )

    wait_between_events()

    emit_event(
        sock,
        "MAC_FLAPPING",
        4,
        f"MAC address {mac_address} continues moving between "
        f"port {interface_1} and port {interface_2}"
    )


# ------------------------------------------------------------
# Kịch bản 5: Vi phạm bảo mật cổng Port Security
# ------------------------------------------------------------

def scenario_port_security_violation(sock):
    """Mô phỏng thiết bị lạ kết nối vào cổng được bảo vệ."""

    interface = random.choice(config.INTERFACES)
    mac_address = "00AA.BBCC.DDEE"

    previous_state = interface_states[interface]

    # Mô phỏng cổng phát hiện vi phạm bảo mật và bị vô hiệu hóa
    port_security_states[interface] = "violation"
    interface_states[interface] = "err-disabled"

    emit_event(
        sock,
        "PORT_SECURITY_VIOLATION",
        2,
        f"Security violation detected on interface {interface}, "
        f"MAC address {mac_address}"
    )

    wait_between_events()

    # Mô phỏng quản trị viên khôi phục cổng mạng
    port_security_states[interface] = "normal"
    interface_states[interface] = previous_state

    emit_event(
        sock,
        "PORT_SECURITY_RECOVERED",
        5,
        f"Simulated Port Security recovery on interface {interface}"
    )


# ------------------------------------------------------------
# Kịch bản 6: Phát hiện vi phạm DHCP Snooping
# ------------------------------------------------------------

def scenario_dhcp_snooping_violation(sock):
    """Mô phỏng DHCP Server không hợp lệ gửi phản hồi DHCP."""

    interface = random.choice(config.INTERFACES)
    vlan = random.choice(config.VLANS)

    emit_event(
        sock,
        "DHCP_SNOOPING_VIOLATION",
        4,
        f"Unauthorized DHCP server detected on interface {interface}, "
        f"VLAN {vlan}"
    )

    wait_between_events()

    emit_event(
        sock,
        "DHCP_SNOOPING_BLOCKED",
        5,
        f"DHCP response from unauthorized server on interface "
        f"{interface} was blocked"
    )


# ------------------------------------------------------------
# Kịch bản 7: Đăng nhập Switch thất bại nhiều lần
# ------------------------------------------------------------

def scenario_unauthorized_login(sock):
    """Mô phỏng nhiều lần đăng nhập thất bại từ cùng một địa chỉ IP."""

    source_ip = "192.168.1.100"
    max_attempts = 5

    # Tăng số lần đăng nhập thất bại và gửi Syslog
    for attempt in range(1, max_attempts + 1):
        login_attempts[source_ip] = (
            login_attempts.get(source_ip, 0) + 1
        )

        emit_event(
            sock,
            "LOGIN_FAILED",
            4,
            f"Login failed from {source_ip}, attempt {attempt}"
        )

        wait_between_events()

    # Phát cảnh báo khi số lần đăng nhập thất bại đạt ngưỡng
    if login_attempts[source_ip] >= max_attempts:
        emit_event(
            sock,
            "LOGIN_THRESHOLD",
            4,
            f"Security alert: {login_attempts[source_ip]} "
            f"failed login attempts detected from {source_ip}"
        )

        # Đặt lại bộ đếm để mô phỏng một chu kỳ giám sát mới
        login_attempts[source_ip] = 0


# ------------------------------------------------------------
# Kịch bản 8: Thay đổi trạng thái Spanning Tree Protocol
# ------------------------------------------------------------

def scenario_stp_topology_change(sock):
    """Mô phỏng sự thay đổi cấu trúc mạng do STP."""

    vlan = random.choice(config.VLANS)

    emit_event(
        sock,
        "STP_TOPOLOGY_CHANGE",
        2,
        f"Topology change detected in VLAN {vlan}"
    )

    wait_between_events()

    emit_event(
        sock,
        "STP_TOPOLOGY_STABLE",
        5,
        f"STP topology in VLAN {vlan} is stable"
    )


# ------------------------------------------------------------
# Kịch bản 9: Một cổng thành viên EtherChannel bị lỗi
# ------------------------------------------------------------

def scenario_etherchannel_failure(sock):
    """Mô phỏng một cổng thành viên trong EtherChannel bị lỗi."""

    # Chỉ chọn nhóm có cổng thành viên
    available_groups = [
        group_id
        for group_id, group_info in etherchannel_states.items()
        if group_info["members"]
    ]

    if not available_groups:
        return

    group_id = random.choice(available_groups)
    group_info = etherchannel_states[group_id]

    interface = random.choice(group_info["members"])
    previous_state = group_info["member_states"][interface]

    # Mô phỏng một cổng thành viên bị mất kết nối
    group_info["member_states"][interface] = "down"
    interface_states[interface] = "down"

    active_members = sum(
        1
        for state in group_info["member_states"].values()
        if state == "up"
    )

    emit_event(
        sock,
        "ETHERCHANNEL_MEMBER_DOWN",
        3,
        f"EtherChannel group {group_id}: member {interface} is down, "
        f"remaining active members: {active_members}"
    )

    wait_between_events()

    # Mô phỏng cổng thành viên hoạt động trở lại
    group_info["member_states"][interface] = previous_state
    interface_states[interface] = previous_state

    emit_event(
        sock,
        "ETHERCHANNEL_MEMBER_RECOVERED",
        5,
        f"EtherChannel group {group_id}: member {interface} "
        f"has been recovered"
    )


# ------------------------------------------------------------
# Kịch bản 10: Quản trị viên thay đổi cấu hình Switch
# ------------------------------------------------------------

def scenario_configuration_change(sock):
    """Mô phỏng quản trị viên thực hiện thay đổi cấu hình."""

    source_ip = "192.168.1.10"

    emit_event(
        sock,
        "CONFIGURATION_CHANGE",
        5,
        f"Configured from console by admin on vty0 ({source_ip})"
    )


# ============================================================
# 4. DANH SÁCH CÁC KỊCH BẢN
# ============================================================

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


# ============================================================
# 5. CHẠY KỊCH BẢN MÔ PHỎNG
# ============================================================

def simulate_switch_event(sock):
    """Chọn ngẫu nhiên và thực hiện một kịch bản."""

    scenario_name, scenario_function = random.choice(SCENARIOS)

    print(f"\n[SCENARIO] {scenario_name}")

    scenario_function(sock)


def start_switch_generator():
    """Khởi động chương trình tạo và gửi Syslog của Switch."""

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print("=" * 55)
    print("SWITCH SYSLOG GENERATOR")
    print("=" * 55)
    print(f"Switch name   : {config.SWITCH_NAME}")
    print(f"Switch IP     : {config.SWITCH_IP}")
    print(f"Syslog server : {config.SYSLOG_SERVER_IP}:{config.SYSLOG_SERVER_PORT}")
    print(f"Protocol      : {config.SYSLOG_PROTOCOL}")
    print(f"Process       : {config.PROCESS_NAME}")
    print(f"Total scenarios: {len(SCENARIOS)}")
    print("Press Ctrl+C to stop the generator.")
    print("=" * 55)

    try:
        while True:
            simulate_switch_event(sock)

            # Nghỉ trước khi bắt đầu kịch bản tiếp theo
            time.sleep(config.SCENARIO_INTERVAL)

    except KeyboardInterrupt:
        print("\n[STOP] Switch Syslog Generator stopped.")

    finally:
        sock.close()
        print("[CLOSED] UDP socket closed.")


# ============================================================
# 6. ĐIỂM BẮT ĐẦU CHƯƠNG TRÌNH
# ============================================================

if __name__ == "__main__":
    start_switch_generator()
