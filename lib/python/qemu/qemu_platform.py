
from lib.python.qemu import QemuBios, QemuUefi


class QemuPlatform:
    QEMU_PLATFORM_I440FX_BIOS = "i440fx+bios"
    QEMU_PLATFORM_Q35_BIOS = "q35+bios"
    QEMU_PLATFORM_Q35_UEFI = "q35+uefi"
    QEMU_PLATFORM_Q35_UEFI_SECURE = "q35+uefi-secure"

    DEFAULT = QEMU_PLATFORM_I440FX_BIOS

    QEMU_PLATFORM_LIST = [QEMU_PLATFORM_I440FX_BIOS, QEMU_PLATFORM_Q35_BIOS, QEMU_PLATFORM_Q35_UEFI,
                          QEMU_PLATFORM_Q35_UEFI_SECURE]

    def __init__(self, vm_meta_data, vm_platform=DEFAULT):
        self.__vm_meta_data = vm_meta_data
        self.__vm_platform = vm_platform
        self.__tpm = None
        if self.is_secure_boot():
            self.__tpm = TpmEmulator(self.__vm_meta_data)

    def before_start_vm(self):
        if self.__tpm is None:
            return
        self.__tpm.start()

    def after_stop_vm(self):
        if self.__tpm is None:
            return
        self.__tpm.close()

    def get_qemu_parameters(self):
        qemu_bios = QemuBios(self.__vm_meta_data)
        if self.__vm_platform == self.QEMU_PLATFORM_Q35_BIOS:
            qemu_bios = QemuBios("q35")
        elif self.__vm_platform == self.QEMU_PLATFORM_Q35_UEFI:
            qemu_bios = QemuUefi(self.__vm_meta_data, is_secure_boot=False)
        elif self.__vm_platform == self.QEMU_PLATFORM_Q35_UEFI_SECURE:
            qemu_bios = QemuUefi(self.__vm_meta_data, is_secure_boot=True)

        result = qemu_bios.get_qemu_parameters()
        if self.__tpm is not None:
            result.extend(self.__tpm.get_qemu_parameters())
        return result

    def is_bios_boot(self):
        return self.is_i440fx_bios_boot() or self.__vm_platform in self.get_bios_boot_platform_list()

    def is_i440fx_bios_boot(self):
        return self.__vm_platform is None or self.__vm_platform in self.get_i440fx_bios_boot_platform_list()

    def is_uefi_boot(self):
        return self.__vm_platform is not None and (self.__vm_platform in self.get_uefi_boot_platform_list())

    def is_secure_boot(self):
        return self.__vm_platform is not None and (self.__vm_platform in self.get_secure_boot_platform_list())

    def get_bios_boot_platform_list(self):
        return [self.QEMU_PLATFORM_I440FX_BIOS, self.QEMU_PLATFORM_Q35_BIOS]

    def get_i440fx_bios_boot_platform_list(self):
        return [self.QEMU_PLATFORM_I440FX_BIOS]

    def get_uefi_boot_platform_list(self):
        return [self.QEMU_PLATFORM_Q35_UEFI, self.QEMU_PLATFORM_Q35_UEFI_SECURE]

    def get_secure_boot_platform_list(self):
        return [self.QEMU_PLATFORM_Q35_UEFI_SECURE]