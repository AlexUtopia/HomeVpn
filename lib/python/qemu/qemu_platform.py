from lib.python.qemu import QemuSeabios, QemuUefi, TpmEmulator
from lib.python.vm import QemuPlatform as QemuPlatformBase, VmMetaData


class QemuPlatform:
    def __init__(self, vm_meta_data: VmMetaData):
        self.__vm_meta_data = vm_meta_data
        self.__tpm: TpmEmulator | None = None
        if self.__vm_meta_data.get_platform().is_uefi_secure_boot():
            self.__tpm = TpmEmulator(self.__vm_meta_data)

    def __enter__(self) -> None:
        if not self.__tpm:
            return
        self.__tpm.start()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if not self.__tpm:
            return
        self.__tpm.close()

    def get_qemu_parameters(self) -> list[dict]:
        qemu_boot = None

        platform = self.__vm_meta_data.get_platform()
        arch = platform.get_arch()
        machine = platform.get_machine()
        if arch.is_x86_compat():
            qemu_boot = QemuSeabios(self.__vm_meta_data)
            if machine == QemuPlatformBase.X86Compat.QEMU_MACHINE_Q35_BIOS:
                qemu_boot = QemuSeabios(self.__vm_meta_data, machine="q35")
            elif machine == QemuPlatformBase.X86Compat.QEMU_MACHINE_Q35_UEFI:
                qemu_boot = QemuUefi(self.__vm_meta_data, is_secure_boot=False)
            elif machine == QemuPlatformBase.X86Compat.QEMU_MACHINE_Q35_UEFI_SECURE:
                qemu_boot = QemuUefi(self.__vm_meta_data, is_secure_boot=True)
        elif arch.is_arm_compat():
            if machine == QemuPlatformBase.ArmCompat.QEMU_MACHINE_VIRT_UEFI:
                qemu_boot = QemuUefi(self.__vm_meta_data, machine="virt", is_secure_boot=False)
            elif machine == QemuPlatformBase.ArmCompat.QEMU_MACHINE_VIRT_UEFI_SECURE:
                qemu_boot = QemuUefi(self.__vm_meta_data, machine="virt", is_secure_boot=True)
            elif machine == QemuPlatformBase.ArmCompat.QEMU_MACHINE_VIRT_UBOOT:
                raise Exception("[QemuPlatform] Uboot now UNSUPPORTED")

        if not qemu_boot:
            return list()

        result = qemu_boot.get_qemu_parameters()
        if self.__tpm:
            result.extend(self.__tpm.get_qemu_parameters())
        return result
