import pathlib

from current_os import CurrentOs


class Platform:
    CHASSIS_TYPE_DESKTOP = 3
    CHASSIS_TYPE_LOW_PROFILE_DESKTOP = 4
    CHASSIS_TYPE_PIZZA_BOX = 5
    CHASSIS_TYPE_MINI_TOWER = 6
    CHASSIS_TYPE_TOWER = 7
    CHASSIS_TYPE_PORTABLE = 8
    CHASSIS_TYPE_LAPTOP = 9
    CHASSIS_TYPE_NOTEBOOK = 10
    CHASSIS_TYPE_HAND_HELD = 11
    CHASSIS_TYPE_DOCKING_STATION = 12
    CHASSIS_TYPE_ALL_IN_ONE = 13
    CHASSIS_TYPE_SUB_NOTEBOOK = 14
    CHASSIS_TYPE_SPACE_SAVING = 15
    CHASSIS_TYPE_LUNCH_BOX = 16
    CHASSIS_TYPE_MAIN_SYSTEM_CHASSIS = 17
    CHASSIS_TYPE_EXPANSION_CHASSIS = 18
    CHASSIS_TYPE_SUB_CHASSIS = 19
    CHASSIS_TYPE_BUS_EXPANSION_CHASSIS = 20
    CHASSIS_TYPE_PERIPHERAL_CHASSIS = 21
    CHASSIS_TYPE_STORAGE_CHASSIS = 22
    CHASSIS_TYPE_RACK_MOUNT_CHASSIS = 23
    CHASSIS_TYPE_SEALED_CASE_PC = 24

    def __init__(self):
        pass

    def is_laptop(self) -> bool:
        return self.get_chassis_type() in [self.CHASSIS_TYPE_PORTABLE,
                                           self.CHASSIS_TYPE_LAPTOP,
                                           self.CHASSIS_TYPE_NOTEBOOK,
                                           self.CHASSIS_TYPE_SUB_NOTEBOOK]

    def get_chassis_type(self) -> int | None:
        if CurrentOs.is_linux():
            return int(pathlib.Path("/sys/devices/virtual/dmi/id/chassis_type").read_text())
        elif CurrentOs.is_windows():
            # https://stackoverflow.com/questions/55184682/powershell-getting-chassis-types-info
            return None
        else:
            return None
