# ==========================================
# CISCO XR ROUTER CONFIGURATION
# ==========================================

# Simulated device identity.
# ROUTER_IP is a configured lab identity; it is NOT necessarily the
# UDP source IP observed by the Syslog receiver.
ROUTER_NAME = "ASR9K-R1"
ROUTER_IP = "192.168.1.1"

# Cisco XR node/card identifier from the VNPT sample.
# NODE_ID is not the router hostname.
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
SYSLOG_PROTOCOL = "UDP"

# Scenario interval (seconds)
SCENARIO_INTERVAL = 5

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
