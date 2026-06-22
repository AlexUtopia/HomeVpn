import pathlib

from lib.python.vm import VmMetaData


class QemuSeabios:
    def __init__(self, vm_meta_data: VmMetaData, machine: str | None = None):
        self.__vm_meta_data = vm_meta_data
        self.__machine = machine

    # SeaBIOS используется по умолчанию, дополнительные аргументы не требуются
    def get_qemu_parameters(self) -> list[dict]:
        # https://www.seabios.org/Debugging
        # https://forums.gentoo.org/viewtopic-p-8812362.html?sid=f8b324e3711f9796b6a777e198212a6d
        result = [{"-chardev": {"file": {"path": self.__get_log_file_path(), "id": "seabios"}}, "-device": {
            "isa-debugcon": {"iobase": 0x402, "chardev": "seabios"}}}]
        if self.__machine:
            result.append({"-machine": self.__machine})
        return result

    def __get_log_file_path(self) -> pathlib.Path:
        return self.__vm_meta_data.get_working_dir_path() / "seabios.log"
