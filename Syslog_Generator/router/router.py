import random
import socket
import time
from datetime import datetime

from . import config


# ==========================================
# ROUTER INTERFACE STATE
# ==========================================

# Initial state of each interface
interface_states = {}

for interface in config.INTERFACES:
    interface_states[interface] = "Up"


# ==========================================
# GENERATE CISCO XR TIMESTAMP
# ==========================================

def get_timestamp():

    now = datetime.now().astimezone()

    timestamp = now.strftime("%b %d %H:%M:%S.%f")[:-3]

    timezone_offset = now.strftime("%z")

    timezone_formatted = (
        timezone_offset[:3] + timezone_offset[3:]
    )

    return f"{timestamp} {timezone_formatted}"


# ==========================================
# GENERATE CISCO XR SYSLOG
# ==========================================

def generate_syslog(interface, new_state):

    timestamp = get_timestamp()

    process_name = "ifmgr"
    process_id = 193

    severity = 3
    message_code = "PKT_INFRA-LINK-3-UPDOWN"

    message_text = (
        f"Interface {interface}, changed state to {new_state}"
    )

    syslog_message = (
        f"{config.NODE_ID}:"
        f"{timestamp}: "
        f"{process_name}[{process_id}]: "
        f"%{message_code} : "
        f"{message_text}"
    )

    return syslog_message


# ==========================================
# SEND SYSLOG MESSAGE
# ==========================================

def send_syslog(sock, message):

    server_address = (
        config.SYSLOG_SERVER_IP,
        config.SYSLOG_SERVER_PORT
    )

    try:
        sock.sendto(
            message.encode("utf-8"),
            server_address
        )

        print(f"[SENT] {message}")

    except OSError as error:
        print(f"[ERROR] Cannot send Syslog: {error}")


# ==========================================
# SIMULATE INTERFACE STATE CHANGES
# ==========================================

def simulate_interface_event(sock):

    interface = random.choice(config.INTERFACES)

    current_state = interface_states[interface]

    # Change interface to the opposite state
    if current_state == "Up":
        new_state = "Down"
    else:
        new_state = "Up"

    # Update interface state
    interface_states[interface] = new_state

    # Generate Syslog
    log_message = generate_syslog(
        interface,
        new_state
    )

    # Send Syslog
    send_syslog(sock, log_message)


# ==========================================
# START ROUTER GENERATOR
# ==========================================

def start_router_generator():

    print("==========================================")
    print("       CISCO XR ROUTER LOG GENERATOR")
    print("==========================================")
    print(f"Router Name : {config.ROUTER_NAME}")
    print(f"Router IP   : {config.ROUTER_IP}")
    print(f"Node ID     : {config.NODE_ID}")
    print(f"Syslog IP   : {config.SYSLOG_SERVER_IP}")
    print(f"Syslog Port : {config.SYSLOG_SERVER_PORT}")
    print("==========================================")
    print("Generating interface UP/DOWN logs...")
    print("Press Ctrl + C to stop.")
    print()

    sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM
    )

    try:
        while True:

            simulate_interface_event(sock)

            time.sleep(config.LOG_INTERVAL)

    except KeyboardInterrupt:
        print("\nRouter Log Generator stopped.")

    finally:
        sock.close()


# ==========================================
# PROGRAM ENTRY POINT
# ==========================================

if __name__ == "__main__":
    start_router_generator()