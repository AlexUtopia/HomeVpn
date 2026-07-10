import hashlib
import json
import os
import pathlib

from lib.python.system import Arch
from lib.python.types import Path, TextConfigWriter
from lib.python.vm import VmMetaData

from lib.python.pci import Pci, PciVidPid


class BasePath:
    def __init__(self, arch: Arch, base_dir_path: str | os.PathLike[str] | None = None):
        self.__arch = arch
        self.__base_dir_path = Path(base_dir_path) if base_dir_path else Path("data")

    def get_ovmf_base_dir_path(self):
        return self.__base_dir_path / "ovmf" / os.environ["CONFIG_OVMF_VERSION"] / str(self.__arch)

    def get_platform_specific_base_dir_path(self):
        return self.__base_dir_path / "platform_specific" / str(self.__arch)


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


class PlatformDescriptor:
    PLATFORM_DESCRIPTOR_FILE_NAME = "platform.json"

    def __init__(self, base_dir_path: str | os.PathLike[str]):
        self.__base_dir_path = Path(base_dir_path)
        self.__dmi = Dmi()

    def get_dir_path(self, is_write_descriptor_file: bool = False) -> Path:
        platform_descriptor_file_content = self.__dmi.get_as_json()
        platform_id = f"platform_{hashlib.md5(platform_descriptor_file_content.encode(self.__dmi.ENCODING)).hexdigest()}"
        platform_specific_roms_dir_path = self.__base_dir_path / platform_id

        if is_write_descriptor_file:
            TextConfigWriter(platform_specific_roms_dir_path / self.PLATFORM_DESCRIPTOR_FILE_NAME,
                             encoding=self.__dmi.ENCODING).set(platform_descriptor_file_content)
        return platform_specific_roms_dir_path


# fixme utopia Скрипт сборки VfioIgdPkg (с учётом pci_vid_pid)
#   Также учитываем возможность извлечения IntelGopDriver.efi из UEFI
class VfioIgdPkgRom:
    def __init__(self, base_path: BasePath, pci_vid_pid: PciVidPid, base_name: str = "ivbios"):
        self.__base_path = base_path
        self.__pci_vid_pid = pci_vid_pid
        self.__base_name = base_name

    def get_paths(self, is_write_descriptor_file: bool = False) -> tuple[Path, Path, Path]:
        pci_device_dir_name = f"{self.__pci_vid_pid.to_path_compat_str()}"
        device_specific_roms_dir_path = self.__get_ovmf_base_dir_path() / pci_device_dir_name
        platform_specific_roms_dir_path = PlatformDescriptor(device_specific_roms_dir_path).get_dir_path(
            is_write_descriptor_file)
        platform_specific_legacy_roms_dir_path = PlatformDescriptor(
            self.__get_platform_specific_base_dir_path()).get_dir_path(is_write_descriptor_file)

        rom_file_path = device_specific_roms_dir_path / f"{self.__base_name}.rom"
        platform_specific_rom_file_path = platform_specific_roms_dir_path / f"{self.__base_name}.rom"
        intel_gop_driver_file_path = platform_specific_legacy_roms_dir_path / f"IntelGopDriver.efi"
        return rom_file_path, platform_specific_rom_file_path, intel_gop_driver_file_path

    def __get_ovmf_base_dir_path(self) -> Path:
        return self.__base_path.get_ovmf_base_dir_path() / "VfioIgdPkg"

    def __get_platform_specific_base_dir_path(self) -> Path:
        return self.__base_path.get_platform_specific_base_dir_path()


# fixme utopia Скрипт сборки i915ovmf (с учётом pci_vid_pid, пока не переиначиваем исходники i915ovmf на строгое соответствие PCI VID/PID)
class i915ovmfRom:
    def __init__(self, base_path: BasePath, pci_vid_pid: PciVidPid, base_name: str = "ivbios"):
        self.__base_path = base_path
        self.__pci_vid_pid = pci_vid_pid
        self.__base_name = base_name

    def get_path(self) -> Path:
        pci_device_dir_name = f"{self.__pci_vid_pid.to_path_compat_str()}"
        device_specific_roms_dir_path = self.__get_ovmf_base_dir_path() / pci_device_dir_name
        rom_file_path = device_specific_roms_dir_path / f"{self.__base_name}.rom"
        return rom_file_path

    def __get_ovmf_base_dir_path(self) -> Path:
        return self.__base_path.get_ovmf_base_dir_path() / "i915ovmf"


# fixme utopia Скрипт извлечения vbios из bios
# https://docs.google.com/document/d/1Eu_OUxyHhhJGlskA6SXyTgKoSnlxXQAfCDY_4iGS71U/edit?usp=sharing
# https://www.dmtf.org/sites/default/files/standards/documents/DSP0134_3.6.0.pdf
# Вот этот вариант проверить
# https://docs.google.com/document/d/131dLrj4e7dF8uLi160n3zIXdlfLO3GTMrnnv3IWwVKk/edit?usp=sharing
# https://github.com/platomav/BIOSUtilities
# fixme utopia Скрипт извлечения vbios из uefi
class LegacyVideoBiosRom:
    def __init__(self, base_path: BasePath, base_name: str = "ivbios"):
        self.__base_path = base_path
        self.__base_name = base_name

    def get_path(self, is_write_descriptor_file: bool = False) -> Path:
        platform_specific_legacy_roms_dir_path = PlatformDescriptor(
            self.__get_platform_specific_base_dir_path()).get_dir_path(is_write_descriptor_file)

        platform_specific_legacy_rom_file_path = platform_specific_legacy_roms_dir_path / f"legacy_{self.__base_name}.rom"
        return platform_specific_legacy_rom_file_path

    def __get_platform_specific_base_dir_path(self) -> Path:
        return self.__base_path.get_platform_specific_base_dir_path()
