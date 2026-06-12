import hashlib
import json
import os
import pathlib

from lib.python.pci import PciVidPid
from lib.python.system import CurrentOs
from lib.python.types import Path, TextConfigWriter
from lib.python.vm import VmMetaData


class Ovmf:
    class Dmi:
        ENCODING = "utf-8"
        ID_DIR_PATH = pathlib.Path("/sys/class/dmi/id")
        PARAMETER_LIST = ["board_vendor", "board_name", "bios_vendor", "bios_version", "bios_date"]

        def __init__(self):
            pass

        def get_as_json(self) -> str:
            return json.dumps(self.get(), indent=4, sort_keys=True)

        def get(self) -> dict[str, str]:
            result = dict()
            for parameter_name in self.PARAMETER_LIST:
                result[parameter_name] = self.__get_parameter_value(parameter_name)
            return result

        def __get_parameter_value(self, parameter_value: str) -> str:
            return (self.ID_DIR_PATH / parameter_value).read_text(encoding=self.ENCODING)

    class PciDeviceRom:
        def __init__(self, base_dir_path: str | os.PathLike[str], pci_vid_pid: PciVidPid, base_name: str = "ivbios"):
            self.__base_dir_path = pathlib.Path(base_dir_path)
            self.__pci_vid_pid = pci_vid_pid
            self.__base_name = base_name
            self.__dmi = Ovmf.Dmi()

        def get_paths(self, is_write_descriptor_file: bool = False) -> tuple[pathlib.Path, pathlib.Path]:
            platform_descriptor_file_content = self.__dmi.get_as_json()
            pci_device_dir_name = f"{self.__pci_vid_pid.to_path_compat_str()}"
            platform_hash = hashlib.md5(platform_descriptor_file_content.encode(self.__dmi.ENCODING)).hexdigest()
            platform_specific_roms_dir_path = self.__base_dir_path / pci_device_dir_name / platform_hash
            platform_descriptor_file_path = platform_specific_roms_dir_path / "platform.json"
            if is_write_descriptor_file:
                TextConfigWriter(platform_descriptor_file_path, encoding=self.__dmi.ENCODING).set(
                    platform_descriptor_file_content)
            rom_file_path = self.__base_dir_path / pci_device_dir_name / f"{self.__base_name}.rom"
            platform_specific_rom_file_path = platform_specific_roms_dir_path / f"{self.__base_name}.rom"
            return rom_file_path, platform_specific_rom_file_path

    def __init__(self, vm_meta_data: VmMetaData, base_dir_path: str | os.PathLike[str] | None = None,
                 is_secure_boot: bool = True):
        self.__vm_meta_data = vm_meta_data
        self.__base_dir_path = Path(base_dir_path) if base_dir_path else Path("data") / "ovmf" / \
                                                                         os.environ[
                                                                             "CONFIG_OVMF_VERSION"] / CurrentOs.get_name() / self.__vm_meta_data.get_arch()
        self.__is_secure_boot = is_secure_boot

    def get_paths(self) -> tuple[Path, Path]:
        return (self.__base_dir_path / self.__get_ovmf_code_file_name(),
                self.__base_dir_path / self.__get_ovmf_vars_file_name())

    def __get_ovmf_code_file_name(self) -> str:
        return self.__get_ovmf_file_name("CODE")

    def __get_ovmf_vars_file_name(self) -> str:
        return self.__get_ovmf_file_name("VARS")

    def __get_ovmf_file_name(self, target: str) -> str:
        return f"OVMF_{target}{'.secboot' if self.__is_secure_boot else ''}.fd"

    # https://www.dmtf.org/sites/default/files/standards/documents/DSP0134_3.2.0.pdf


# https://github.com/tianocore/edk2/blob/master/OvmfPkg/README
# https://superuser.com/a/1798353/2121020
# https://www.qemu.org/docs/master/system/invocation.html#hxtool-0
class QemuUefi:
    PREFIX = "uefi"

    def __init__(self, vm_meta_data: VmMetaData, is_secure_boot=True):
        self.__vm_meta_data = vm_meta_data
        self.__ovmf = Ovmf(self.__vm_meta_data, is_secure_boot=is_secure_boot)

    def get_qemu_parameters(self) -> list[dict]:
        ovmf_code_file_path, ovmf_vars_file_path = self.__get_vm_ovmf_paths()
        return [
            {"-machine": "q35"},
            {"-drive": {
                "if": "pflash", "format": "raw", "file": ovmf_code_file_path, "readonly": "on"}},
            {"-drive": {
                "if": "pflash", "format": "raw", "file": ovmf_vars_file_path}}]

    def __get_vm_ovmf_paths(self) -> tuple[Path, Path]:
        ovmf_code_file_path, ovmf_vars_file_path = self.__ovmf.get_paths()
        return self.__copy_if_non_exists(ovmf_code_file_path), self.__copy_if_non_exists(ovmf_vars_file_path)

    def __copy_if_non_exists(self, path: Path) -> Path:
        result = self.__get_vm_ovmf_path(path)
        if not result.exists():
            result.parent.makedirs()
            result.copy_from(path)
        return result

    def __get_vm_ovmf_path(self, path: Path) -> Path:
        return self.__get_uefi_state_dir_path() / path.name

    def __get_uefi_state_dir_path(self) -> Path:
        return self.__vm_meta_data.get_working_dir_path() / self.PREFIX
