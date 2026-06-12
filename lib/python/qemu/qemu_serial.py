import pathlib

from lib.python.vm import VmMetaData


# https://superuser.com/a/1412150/2121020
class QemuSerial:
    PREFIX = "serial"

    __index = -1

    def __init__(self, vm_meta_data: VmMetaData):
        QemuSerial.__index += 1
        self.__vm_meta_data = vm_meta_data

    def get_qemu_parameters(self) -> list[dict]:
        self.__get_serial_state_dir_path().mkdir(parents=True, exist_ok=True)
        return [{"-chardev": {
            "file": {"id": self.__get_serial_chardev_id(), "mux": "on", "path": self.__get_serial_log_file_path(),
                     "signal": "off"}}}, {"-serial": f"chardev:{self.__get_serial_chardev_id()}"}]

    def __get_serial_chardev_id(self):
        return f"{self.PREFIX}-{self.__vm_meta_data.get_name()}-chardev-id{self.__index}"

    def __get_serial_log_file_path(self) -> pathlib.Path:
        return self.__get_serial_state_dir_path() / f"{self.PREFIX}{self.__index}.log"

    def __get_serial_state_dir_path(self) -> pathlib.Path:
        return self.__vm_meta_data.get_working_dir_path() / self.PREFIX
