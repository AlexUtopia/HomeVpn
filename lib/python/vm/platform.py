import typing

from lib.python.system import Arch


# qemu-system-{VmMetaData.get_arch()} -machine help
# https://share.google/aimode/NHiO5vvQrgg9PgWCW
# Добавить метод is_uboot()
# https://docs.u-boot.org/en/stable/board/emulation/qemu-arm.html
class QemuPlatform:
    class OsBootDescriptor(typing.Protocol):
        def get_default_machine(self) -> str:
            ...

        def get_machine_list(self) -> set[str]:
            ...

        def get_bios_boot_machine_list(self) -> set[str]:
            ...

        def get_uefi_boot_machine_list(self) -> set[str]:
            ...

        def get_uefi_secure_boot_machine_list(self) -> set[str]:
            ...

        def get_i440fx_bios_boot_machine_list(self) -> set[str]:
            ...

    class X86Compat:
        QEMU_MACHINE_I440FX_BIOS = "i440fx+bios"
        QEMU_MACHINE_Q35_BIOS = "q35+bios"
        QEMU_MACHINE_Q35_UEFI = "q35+uefi"
        QEMU_MACHINE_Q35_UEFI_SECURE = "q35+uefi-secure"

        DEFAULT = QEMU_MACHINE_I440FX_BIOS

        QEMU_MACHINE_LIST = {QEMU_MACHINE_I440FX_BIOS, QEMU_MACHINE_Q35_BIOS, QEMU_MACHINE_Q35_UEFI,
                             QEMU_MACHINE_Q35_UEFI_SECURE}

        def get_default_machine(self) -> str:
            return self.DEFAULT

        def get_machine_list(self) -> set[str]:
            return self.QEMU_MACHINE_LIST

        def get_bios_boot_machine_list(self) -> set[str]:
            return {self.QEMU_MACHINE_I440FX_BIOS, self.QEMU_MACHINE_Q35_BIOS}

        def get_uefi_boot_machine_list(self) -> set[str]:
            return {self.QEMU_MACHINE_Q35_UEFI, self.QEMU_MACHINE_Q35_UEFI_SECURE}

        def get_uefi_secure_boot_machine_list(self) -> set[str]:
            return {self.QEMU_MACHINE_Q35_UEFI_SECURE}

        def get_i440fx_bios_boot_machine_list(self) -> set[str]:
            return {self.QEMU_MACHINE_I440FX_BIOS}

    class ArmCompat:
        QEMU_MACHINE_VIRT_UBOOT = "virt+uboot"
        QEMU_MACHINE_VIRT_UEFI = "virt+uefi"
        QEMU_MACHINE_VIRT_UEFI_SECURE = "virt+uefi-secure"

        DEFAULT = QEMU_MACHINE_VIRT_UEFI

        QEMU_MACHINE_LIST = {QEMU_MACHINE_VIRT_UBOOT, QEMU_MACHINE_VIRT_UEFI, QEMU_MACHINE_VIRT_UEFI_SECURE}

        def get_default_machine(self) -> str:
            return self.DEFAULT

        def get_machine_list(self) -> set[str]:
            return self.QEMU_MACHINE_LIST

        def get_bios_boot_machine_list(self) -> set[str]:
            return set()

        def get_uefi_boot_machine_list(self) -> set[str]:
            return {self.QEMU_MACHINE_VIRT_UEFI, self.QEMU_MACHINE_VIRT_UEFI}

        def get_uefi_secure_boot_machine_list(self) -> set[str]:
            return {self.QEMU_MACHINE_VIRT_UEFI_SECURE}

        def get_i440fx_bios_boot_machine_list(self) -> set[str]:
            return set()

    __BOOT_TABLE = {Arch("x86_64"): X86Compat(),
                    Arch("i386"): X86Compat(),
                    Arch("aarh64"): ArmCompat(),
                    Arch("arm"): ArmCompat()}

    def __init__(self, arch_and_machine: str | None = None, arch: Arch = Arch(), machine: str | None = None):
        if arch_and_machine:
            maxsplit = 2
            arch_vs_machine = arch_and_machine.split(":", maxsplit=maxsplit)
            arch = Arch(arch_vs_machine[0])
            if len(arch_vs_machine) == maxsplit:
                machine = arch_vs_machine[1]

        os_boot_descriptor = QemuPlatform.__BOOT_TABLE.get(arch, None)
        if not os_boot_descriptor:
            raise Exception(
                f"[Qemumachine] Unknown arch ({arch}). Available: {', '.join([str(_arch) for _arch, _ in QemuPlatform.__BOOT_TABLE.items()])}")

        if machine:
            self.__machine = machine
            if self.__machine not in os_boot_descriptor.get_machine_list():
                raise Exception(
                    f"[Qemumachine] Unknown machine ({machine}). Available: {', '.join(os_boot_descriptor.get_machine_list())}")
        else:
            self.__machine = os_boot_descriptor.get_default_machine()

        self.__arch = arch
        self.__os_boot_descriptor = os_boot_descriptor

    def get_arch(self) -> Arch:
        return self.__arch

    def get_machine(self) -> str:
        return self.__machine

    def is_bios_boot(self) -> bool:
        return self.__machine in self.__os_boot_descriptor.get_bios_boot_machine_list()

    def is_i440fx_bios_boot(self) -> bool:
        return self.__machine in self.__os_boot_descriptor.get_i440fx_bios_boot_machine_list()

    def is_uefi_boot(self) -> bool:
        return self.__machine in self.__os_boot_descriptor.get_uefi_boot_machine_list()

    def is_uefi_secure_boot(self) -> bool:
        return self.__machine in self.__os_boot_descriptor.get_uefi_secure_boot_machine_list()
