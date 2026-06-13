import os
import subprocess

from lib.python.logger import Logger
from lib.python.network import TcpPort
from lib.python.types import Path

from lib.python.vm import VmName, VmMetaData


class VmRegistry:
    __IMAGE_FORMAT = "qcow2"

    def __init__(self, vm_registry_dir_path: os.PathLike[str] | str):
        self.__vm_registry_dir_path = Path(vm_registry_dir_path).resolve()

    def get_path(self) -> Path:
        return self.__vm_registry_dir_path

    def create(self, name: VmName | str, image_size_in_gib: int = 20) -> VmMetaData:
        result = self.get(name)
        if result:
            raise Exception(
                f'[Vm] Image "{result.get_image_path()}" EXISTS. Please change VM name')
        else:
            result = VmMetaData(name, self.__vm_registry_dir_path / str(name))

        command_line = self.__create_image_command_line(result, image_size_in_gib)
        Logger.instance().debug(f"[Vm] Create image cmd: {command_line}")
        subprocess.check_call(command_line, shell=True)
        return result

    def list(self) -> set[VmMetaData]:
        result = set()
        if not self.__vm_registry_dir_path.exists() or not self.__vm_registry_dir_path.is_dir():
            return result

        for path in self.__vm_registry_dir_path.iterdir():
            if path.is_dir() or path.resolve().is_dir():
                vm_meta_data = VmMetaData(path.name, path)
                if vm_meta_data.image_exists():
                    result.add(vm_meta_data)
        return result

    def get_with_verifying(self, name: VmName | str) -> VmMetaData:
        result = self.get(name)
        if not result:
            raise Exception(f'[Vm] Image "{name}" NOT FOUND')
        return result

    def get(self, name) -> VmMetaData | None:
        for vm_meta_data in self.list():
            if vm_meta_data == name:
                return vm_meta_data
        return None

    def set_ssh_forward_port(self, name: VmName | str, ssh_forward_port: TcpPort | int):
        meta_data = self.get_with_verifying(name)
        meta_data.set_ssh_forward_port(ssh_forward_port)

    def set_rdp_forward_port(self, name: VmName | str, rdp_forward_port: TcpPort | int):
        meta_data = self.get_with_verifying(name)
        meta_data.set_rdp_forward_port(rdp_forward_port)

    def __create_image_command_line(self, vm_meta_data: VmMetaData, image_size_in_gib: int):
        return f'qemu-img create -f {self.__IMAGE_FORMAT} "{vm_meta_data.get_image_path()}" {image_size_in_gib}G'