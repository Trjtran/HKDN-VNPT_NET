
# ==========================================
# SWITCH CONFIGURATION
# ==========================================

# Thông tin Switch
SWITCH_NAME = "SW-LAB-01"
SWITCH_IP = "192.168.1.2"

# Node ID dùng trong định dạng Syslog chung
NODE_ID = SWITCH_NAME

# Tên tiến trình gửi Syslog
PROCESS_NAME = "switch_sim[193]"

# Danh sách cổng mạng của Switch
INTERFACES = [
    "GigabitEthernet1/0/1",
    "GigabitEthernet1/0/2",
    "GigabitEthernet1/0/3",
    "GigabitEthernet1/0/4"
]

# Danh sách VLAN mô phỏng
VLANS = [10, 20, 30]

# Cấu hình Syslog Server
SYSLOG_SERVER_IP = "127.0.0.1"
SYSLOG_SERVER_PORT = 5514
SYSLOG_PROTOCOL = "UDP"

# Thời gian chờ giữa các sự kiện (giây)
LOG_INTERVAL = 5
SCENARIO_INTERVAL = 5
