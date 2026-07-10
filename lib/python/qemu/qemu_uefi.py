from lib.python.pci import BasePath
from lib.python.types import Path
from lib.python.vm import VmMetaData


class Ovmf:
    def __init__(self, vm_meta_data: VmMetaData, base_path: BasePath | None = None,
                 is_secure_boot: bool = True):
        self.__vm_meta_data = vm_meta_data
        self.__base_path = base_path if base_path else BasePath(self.__vm_meta_data.get_platform().get_arch())
        self.__is_secure_boot = is_secure_boot

    def get_paths(self) -> tuple[Path, Path]:
        base_dir_path = self.__base_path.get_ovmf_base_dir_path()
        return (base_dir_path / self.__get_ovmf_code_file_name(),
                base_dir_path / self.__get_ovmf_vars_file_name())

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

    def __init__(self, vm_meta_data: VmMetaData, machine: str = "q35", is_secure_boot=True):
        self.__vm_meta_data = vm_meta_data
        self.__machine = machine
        self.__ovmf = Ovmf(self.__vm_meta_data, is_secure_boot=is_secure_boot)

    def get_qemu_parameters(self) -> list[dict]:
        ovmf_code_file_path, ovmf_vars_file_path = self.__get_vm_ovmf_paths()
        return [
            {"-machine": self.__machine},
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
