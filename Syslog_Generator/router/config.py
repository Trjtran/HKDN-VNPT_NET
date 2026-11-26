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

# ==========================================
# BGP NEIGHBOR CONFIGURATION
# ==========================================

BGP_NEIGHBORS = [
    "10.10.10.2",
    "10.10.10.3"
]

# ==========================================
# CPU / MEMORY CONFIGURATION
# ==========================================

CPU_WARNING_THRESHOLD = 80
MEMORY_WARNING_THRESHOLD = 85

# ==========================================
# HARDWARE CONFIGURATION
# ==========================================

NORMAL_TEMPERATURE = 45
HIGH_TEMPERATURE = 85

HARDWARE_COMPONENTS = [
    "Fan 0/0",
    "Fan 0/1",
    "Power Supply 0/0",
    "Power Supply 0/1"
]

# ==========================================
# NETWORK PERFORMANCE CONFIGURATION
# ==========================================

PACKET_LOSS_THRESHOLD = 5
INTERFACE_ERROR_THRESHOLD = 100

# ==========================================
# SCENARIO CONFIGURATION
# ==========================================

SCENARIO_INTERVAL = 5
