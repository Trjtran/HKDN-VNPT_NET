import socket
import time

from . import config
from .scenarios import RouterScenarioManager
from .state_manager import InterfaceStateManager


def get_timestamp():
    now = time.localtime()
    timestamp = time.strftime("%b %d %H:%M:%S", now)
    milliseconds = int((time.time() % 1) * 1000)
    timezone_offset = time.strftime("%z")
    timezone_formatted = timezone_offset[:3] + timezone_offset[3:]

    return f"{timestamp}.{milliseconds:03d} {timezone_formatted}"


def generate_syslog(interface, new_state):
    timestamp = get_timestamp()
    message_code = "PKT_INFRA-LINK-3-UPDOWN"
    message_text = f"Interface {interface}, changed state to {new_state}"

    # Keep the Cisco XR interface message structure from the VNPT sample.
    return (
        f"{config.NODE_ID}:"
        f"{timestamp}: "
        f"ifmgr[193]: "
        f"%{message_code} : "
        f"{message_text}"
    )


def generate_synthetic_syslog(event):
    timestamp = get_timestamp()
    event_type = event["type"].upper()
    severity = event["severity"]
    message = event["message"]
    message_code = f"SYNTH-{severity}-{event_type}"

    # SYNTH prefix clearly identifies simulated non-interface events.
    return (
        f"{config.NODE_ID}:"
        f"{timestamp}: "
        f"router_sim[193]: "
        f"%{message_code} : "
        f"{message}"
    )


def send_syslog(sock, message):
    server_address = (
        config.SYSLOG_SERVER_IP,
        config.SYSLOG_SERVER_PORT
    )

    try:
        sock.sendto(message.encode("utf-8"), server_address)
        print(f"[SENT] {message}")
    except OSError as error:
        print(f"[ERROR] Cannot send Syslog: {error}")


def print_interface_status(state_manager):
    print("\n[INTERFACE STATUS]")
    print("-" * 75)

    for interface, info in state_manager.get_all_states().items():
        print(
            f"{interface:<20} | "
            f"Status: {info['status']:<5} | "
            f"Current downtime: {info['current_downtime']}s | "
            f"Last downtime: {info['last_downtime']}s"
        )

    print("-" * 75)


def process_scenario(sock, scenario_name, events, state_manager):
    print()
    print("=" * 60)
    print(f"[SCENARIO] {scenario_name.upper()}")
    print("=" * 60)

    for event in events:
        if event["type"] == "interface":
            interface = event["interface"]
            new_state = event["status"]

            if new_state == "Down":
                event_info = state_manager.set_down(interface)
            else:
                event_info = state_manager.set_up(interface)

            # Ignore duplicate or invalid state transitions.
            if event_info is None:
                continue

            log_message = generate_syslog(interface, new_state)
            send_syslog(sock, log_message)

            if new_state == "Down":
                print(f"[STATUS] {interface} is DOWN")
            else:
                print(
                    f"[RECOVERY] {interface} is UP - "
                    f"Downtime: {event_info['downtime']} seconds"
                )
        else:
            log_message = generate_synthetic_syslog(event)
            send_syslog(sock, log_message)

        time.sleep(1)


def start_router_generator():
    print("=" * 60)
    print("             CISCO XR ROUTER LOG GENERATOR")
    print("=" * 60)
    print(f"Simulated Router Name : {config.ROUTER_NAME}")
    print(f"Configured Router IP  : {config.ROUTER_IP}")
    print(f"Cisco XR Node ID      : {config.NODE_ID}")
    print(f"Syslog Server         : {config.SYSLOG_SERVER_IP}:{config.SYSLOG_SERVER_PORT}")
    print("=" * 60)
    print("Generating router failure scenarios...")
    print("Non-interface events use SYNTH-* codes for simulation.")
    print("Press Ctrl + C to stop.")
    print()

    state_manager = InterfaceStateManager()
    scenario_manager = RouterScenarioManager(state_manager)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        while True:
            scenario_name, events = scenario_manager.generate_scenario()
            process_scenario(
                sock,
                scenario_name,
                events,
                state_manager
            )
            print_interface_status(state_manager)
            time.sleep(config.SCENARIO_INTERVAL)

    except KeyboardInterrupt:
        print("\nRouter Log Generator stopped.")
    finally:
        sock.close()


if __name__ == "__main__":
    start_router_generator()
