import random
from . import config


class RouterScenarioManager:
    def __init__(self, interface_manager):
        self.interface_manager = interface_manager

        # BGP Neighbor
        self.bgp_states = {
            neighbor: "Established"
            for neighbor in config.BGP_NEIGHBORS
        }

        # CPU / Memory
        self.cpu_state = "Normal"
        self.memory_state = "Normal"

        # Hardware
        self.hardware_states = {
            component: "Normal"
            for component in config.HARDWARE_COMPONENTS
        }
        self.temperature_state = "Normal"

        # Network performance
        self.performance_states = {
            "packet_loss": "Normal",
            "interface_error": "Normal"
        }

    # ==========================================
    # INTERFACE SCENARIOS
    # ==========================================

    def normal_interface(self):
        interface = random.choice(config.INTERFACES)
        current = self.interface_manager.get_state(interface)
        new_state = "Down" if current == "Up" else "Up"

        return [{
            "type": "interface",
            "interface": interface,
            "status": new_state
        }]

    def interface_flapping(self):
        interface = random.choice(config.INTERFACES)
        current = self.interface_manager.get_state(interface)
        events = []

        for _ in range(4):
            current = "Down" if current == "Up" else "Up"
            events.append({
                "type": "interface",
                "interface": interface,
                "status": current
            })

        return events

    def multiple_interfaces_down(self):
        available = [
            interface for interface in config.INTERFACES
            if self.interface_manager.get_state(interface) == "Up"
        ]

        if len(available) < 2:
            return self.normal_interface()

        selected = random.sample(available, 2)

        return [{
            "type": "interface",
            "interface": interface,
            "status": "Down"
        } for interface in selected]

    def interface_recovery(self):
        down_interfaces = [
            interface for interface in config.INTERFACES
            if self.interface_manager.get_state(interface) == "Down"
        ]

        if not down_interfaces:
            return self.normal_interface()

        interface = random.choice(down_interfaces)

        return [{
            "type": "interface",
            "interface": interface,
            "status": "Up"
        }]

    # ==========================================
    # BGP NEIGHBOR SCENARIOS
    # ==========================================

    def bgp_event(self):
        neighbor = random.choice(config.BGP_NEIGHBORS)
        current = self.bgp_states[neighbor]
        new_state = "Idle" if current == "Established" else "Established"
        self.bgp_states[neighbor] = new_state

        return [{
            "type": "bgp",
            "message": (
                f"BGP neighbor {neighbor} changed state "
                f"from {current} to {new_state}"
            ),
            "severity": 3 if new_state == "Idle" else 5
        }]

    def bgp_flapping(self):
        neighbor = random.choice(config.BGP_NEIGHBORS)
        events = []
        current = self.bgp_states[neighbor]

        for _ in range(4):
            new_state = "Idle" if current == "Established" else "Established"
            events.append({
                "type": "bgp",
                "message": (
                    f"BGP neighbor {neighbor} changed state "
                    f"from {current} to {new_state}"
                ),
                "severity": 3 if new_state == "Idle" else 5
            })
            current = new_state

        self.bgp_states[neighbor] = current
        return events

    # ==========================================
    # CPU / MEMORY SCENARIOS
    # ==========================================

    def resource_event(self):
        resource = random.choice(["CPU", "Memory"])

        if resource == "CPU":
            threshold = config.CPU_WARNING_THRESHOLD
            current = self.cpu_state
        else:
            threshold = config.MEMORY_WARNING_THRESHOLD
            current = self.memory_state

        # Generate a value consistent with the next state.
        if current == "Normal":
            new_state = "High"
            value = random.randint(threshold, max(threshold, threshold + 15))
        else:
            new_state = "Normal"
            value = random.randint(30, threshold - 1)

        if resource == "CPU":
            self.cpu_state = new_state
        else:
            self.memory_state = new_state

        return [{
            "type": "resource",
            "message": (
                f"{resource} utilization is {value}% "
                f"(threshold: {threshold}%) - state: {new_state}"
            ),
            "severity": 3 if new_state == "High" else 5
        }]

    # ==========================================
    # HARDWARE SCENARIOS
    # ==========================================

    def hardware_event(self):
        component = random.choice(config.HARDWARE_COMPONENTS)
        current = self.hardware_states[component]
        new_state = "Failure" if current == "Normal" else "Normal"
        self.hardware_states[component] = new_state

        if "Fan" in component:
            message = (
                f"Fan failure detected: {component}"
                if new_state == "Failure"
                else f"Fan recovered: {component}"
            )
        else:
            message = (
                f"Power supply failure detected: {component}"
                if new_state == "Failure"
                else f"Power supply recovered: {component}"
            )

        return [{
            "type": "hardware",
            "message": message,
            "severity": 2 if new_state == "Failure" else 5
        }]

    def temperature_event(self):
        if self.temperature_state == "Normal":
            self.temperature_state = "High"
            temperature = random.randint(
                config.HIGH_TEMPERATURE,
                config.HIGH_TEMPERATURE + 15
            )
            severity = 2
            message = (
                f"Temperature threshold exceeded: {temperature} Celsius "
                f"(threshold: {config.HIGH_TEMPERATURE} Celsius)"
            )
        else:
            self.temperature_state = "Normal"
            temperature = random.randint(
                30,
                config.NORMAL_TEMPERATURE
            )
            severity = 5
            message = (
                f"Temperature returned to normal: {temperature} Celsius"
            )

        return [{
            "type": "hardware",
            "message": message,
            "severity": severity
        }]

    # ==========================================
    # NETWORK PERFORMANCE SCENARIOS
    # ==========================================

    def performance_event(self):
        event_type = random.choice(["packet_loss", "interface_error"])
        current = self.performance_states[event_type]

        if event_type == "packet_loss":
            threshold = config.PACKET_LOSS_THRESHOLD
            if current == "Normal":
                self.performance_states[event_type] = "High"
                value = random.randint(threshold, max(threshold, threshold + 15))
                message = (
                    f"Packet loss detected: {value}% "
                    f"(threshold: {threshold}%)"
                )
                severity = 3
            else:
                self.performance_states[event_type] = "Normal"
                value = random.randint(0, max(0, threshold - 1))
                message = f"Packet loss recovered: {value}%"
                severity = 5
        else:
            threshold = config.INTERFACE_ERROR_THRESHOLD
            if current == "Normal":
                self.performance_states[event_type] = "High"
                value = random.randint(threshold, threshold + 100)
                message = (
                    f"Interface errors detected: {value} "
                    f"(threshold: {threshold})"
                )
                severity = 3
            else:
                self.performance_states[event_type] = "Normal"
                value = random.randint(0, max(0, threshold - 1))
                message = f"Interface errors returned to normal: {value}"
                severity = 5

        return [{
            "type": "performance",
            "message": message,
            "severity": severity
        }]

    # ==========================================
    # SYSTEM / SECURITY SCENARIOS
    # ==========================================

    def system_security_event(self):
        event = random.choice([
            "login_failure",
            "config_change",
            "device_reboot"
        ])

        messages = {
            "login_failure": "Failed login attempt detected (simulated)",
            "config_change": "Router configuration changed (simulated)",
            "device_reboot": "Router reboot event simulated"
        }

        severity = {
            "login_failure": 4,
            "config_change": 5,
            "device_reboot": 5
        }

        return [{
            "type": "system_security",
            "message": messages[event],
            "severity": severity[event]
        }]

    # ==========================================
    # MAIN SCENARIO SELECTOR
    # ==========================================

    def generate_scenario(self):
        scenarios = [
            "normal_interface",
            "interface_flapping",
            "multiple_interfaces_down",
            "interface_recovery",
            "bgp_event",
            "bgp_flapping",
            "resource_event",
            "hardware_event",
            "temperature_event",
            "performance_event",
            "system_security_event"
        ]

        weights = [
            20, 5, 5, 5,
            10, 5,
            10,
            10, 5,
            10,
            15
        ]

        selected = random.choices(
            scenarios,
            weights=weights,
            k=1
        )[0]

        events = getattr(self, selected)()
        return selected, events
