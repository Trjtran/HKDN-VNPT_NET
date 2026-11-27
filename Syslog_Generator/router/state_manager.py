import time
from datetime import datetime

from . import config


class InterfaceStateManager:

    def __init__(self):

        # Trạng thái hiện tại của từng Interface
        self.interface_states = {}

        # Thời điểm bắt đầu DOWN
        self.down_start_times = {}

        # Lịch sử thời gian gián đoạn
        self.last_downtime = {}

        for interface in config.INTERFACES:

            self.interface_states[interface] = "Up"

            self.down_start_times[interface] = None

            self.last_downtime[interface] = 0

    # ==========================================
    # GET CURRENT INTERFACE STATE
    # ==========================================

    def get_state(self, interface):

        return self.interface_states.get(interface)

    # ==========================================
    # CHANGE INTERFACE TO DOWN
    # ==========================================

    def set_down(self, interface):

        if interface not in self.interface_states:
            return None

        # Không ghi nhận DOWN lần nữa nếu đã DOWN
        if self.interface_states[interface] == "Down":
            return None

        self.interface_states[interface] = "Down"

        # Dùng monotonic để đo thời gian chính xác
        self.down_start_times[interface] = time.monotonic()

        event_time = datetime.now().astimezone()

        return {
            "interface": interface,
            "status": "Down",
            "event_time": event_time.isoformat(),
            "downtime": None
        }

    # ==========================================
    # CHANGE INTERFACE TO UP
    # ==========================================

    def set_up(self, interface):

        if interface not in self.interface_states:
            return None

        # Chỉ phục hồi khi Interface đang DOWN
        if self.interface_states[interface] != "Down":
            return None

        start_time = self.down_start_times[interface]

        downtime = time.monotonic() - start_time

        self.interface_states[interface] = "Up"

        self.down_start_times[interface] = None

        self.last_downtime[interface] = round(downtime, 2)

        event_time = datetime.now().astimezone()

        return {
            "interface": interface,
            "status": "Up",
            "event_time": event_time.isoformat(),
            "downtime": round(downtime, 2)
        }

    # ==========================================
    # GET CURRENT DOWNTIME
    # ==========================================

    def get_downtime(self, interface):

        if interface not in self.interface_states:
            return None

        if self.interface_states[interface] != "Down":
            return 0

        start_time = self.down_start_times[interface]

        return round(
            time.monotonic() - start_time,
            2
        )

    # ==========================================
    # GET ALL INTERFACE STATES
    # ==========================================

    def get_all_states(self):

        result = {}

        for interface, state in self.interface_states.items():

            result[interface] = {
                "status": state,
                "current_downtime": self.get_downtime(interface),
                "last_downtime": self.last_downtime[interface]
            }

        return result