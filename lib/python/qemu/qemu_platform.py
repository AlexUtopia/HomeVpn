from lib.python.qemu import QemuSeaBios, QemuUefi, TpmEmulator
from lib.python.vm import QemuPlatform as QemuPlatformBase


class QemuPlatform(QemuPlatformBase):
    def __init__(self, vm_meta_data, vm_platform=QemuPlatformBase.DEFAULT):
        super().__init__(vm_platform=vm_platform)
        self.__vm_meta_data = vm_meta_data
        self.__tpm: TpmEmulator | None = None
        if self.is_secure_boot():
            self.__tpm = TpmEmulator(self.__vm_meta_data)

    # fixme utopia Переделать на контексты
    def before_start_vm(self) -> None:
        if not self.__tpm:
            return
        self.__tpm.start()

    def after_stop_vm(self) -> None:
        if not self.__tpm:
            return
        self.__tpm.close()

    def get_qemu_parameters(self) -> list[dict]:
        qemu_bios = QemuSeaBios(self.__vm_meta_data)
        if self.__vm_platform == self.QEMU_PLATFORM_Q35_BIOS:
            qemu_bios = QemuSeaBios(self.__vm_meta_data, chipset="q35")
        elif self.__vm_platform == self.QEMU_PLATFORM_Q35_UEFI:
            qemu_bios = QemuUefi(self.__vm_meta_data, is_secure_boot=False)
        elif self.__vm_platform == self.QEMU_PLATFORM_Q35_UEFI_SECURE:
            qemu_bios = QemuUefi(self.__vm_meta_data, is_secure_boot=True)

        result = qemu_bios.get_qemu_parameters()
        if self.__tpm:
            result.extend(self.__tpm.get_qemu_parameters())
        return result
