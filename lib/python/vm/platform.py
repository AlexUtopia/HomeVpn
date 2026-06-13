

# fixme utopia Приспособить для не x86 платформы
# qemu-system-{VmMetaData.get_arch()} -machine help
# https://share.google/aimode/NHiO5vvQrgg9PgWCW
# Добавить метод is_uboot()
# https://docs.u-boot.org/en/stable/board/emulation/qemu-arm.html
class QemuPlatform:
    QEMU_PLATFORM_I440FX_BIOS = "i440fx+bios"
    QEMU_PLATFORM_Q35_BIOS = "q35+bios"
    QEMU_PLATFORM_Q35_UEFI = "q35+uefi"
    QEMU_PLATFORM_Q35_UEFI_SECURE = "q35+uefi-secure"

    DEFAULT = QEMU_PLATFORM_I440FX_BIOS

    QEMU_PLATFORM_LIST = [QEMU_PLATFORM_I440FX_BIOS, QEMU_PLATFORM_Q35_BIOS, QEMU_PLATFORM_Q35_UEFI,
                          QEMU_PLATFORM_Q35_UEFI_SECURE]

    def __init__(self, vm_platform: str = DEFAULT):
        self.__vm_platform = vm_platform

    def is_bios_boot(self) -> bool:
        return self.is_i440fx_bios_boot() or self.__vm_platform in self.get_bios_boot_platform_list()

    def is_i440fx_bios_boot(self) -> bool:
        return self.__vm_platform in self.get_i440fx_bios_boot_platform_list()

    def is_uefi_boot(self) -> bool:
        return self.__vm_platform in self.get_uefi_boot_platform_list()

    def is_secure_boot(self) -> bool:
        return self.__vm_platform in self.get_secure_boot_platform_list()

    def get_bios_boot_platform_list(self) -> list[str]:
        return [self.QEMU_PLATFORM_I440FX_BIOS, self.QEMU_PLATFORM_Q35_BIOS]

    def get_i440fx_bios_boot_platform_list(self) -> list[str]:
        return [self.QEMU_PLATFORM_I440FX_BIOS]

    def get_uefi_boot_platform_list(self) -> list[str]:
        return [self.QEMU_PLATFORM_Q35_UEFI, self.QEMU_PLATFORM_Q35_UEFI_SECURE]

    def get_secure_boot_platform_list(self) -> list[str]:
        return [self.QEMU_PLATFORM_Q35_UEFI_SECURE]
