# ==========================================
# CISCO XR ROUTER CONFIGURATION
# ==========================================

# Router information
ROUTER_NAME = "ASR9K-R1"
ROUTER_IP = "192.168.1.1"

# Cisco XR node information
NODE_ID = "LC/0/1/CPU0"

# Interface configuration
INTERFACES = [
    "TenGigE0/1/0/4",
    "TenGigE0/1/0/5",
    "TenGigE0/1/0/6"
]

# Syslog Server configuration
SYSLOG_SERVER_IP = "127.0.0.1"
SYSLOG_SERVER_PORT = 5514

# Syslog protocol
SYSLOG_PROTOCOL = "UDP"

# Log generation interval (seconds)
LOG_INTERVAL = 5