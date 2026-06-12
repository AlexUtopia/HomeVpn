import pathlib

from lib.python.vm import VmMetaData


class QemuLogging:
    PREFIX = "qemu"

    def __init__(self, vm_meta_data: VmMetaData):
        self.__vm_meta_data = vm_meta_data

    def get_qemu_parameters(self) -> list[dict]:
        self.__get_qemu_state_dir_path().mkdir(parents=True, exist_ok=True)
        return [{"-D": self.__get_qemu_log_file_path()}]

    def __get_qemu_log_file_path(self) -> pathlib.Path:
        return self.__get_qemu_state_dir_path() / f"{self.PREFIX}.log"

    def __get_qemu_state_dir_path(self) -> pathlib.Path:
        return self.__vm_meta_data.get_working_dir_path() / self.PREFIX
