from lib.python.system import CurrentOs

from lib.python.vm import VmMetaData


class QemuAccel:
    def __init__(self, vm_meta_data: VmMetaData):
        self.__vm_meta_data = vm_meta_data

    # Проверять наличие активированного (работоспособного) акселератора не будем
    # Для kvm проверить можно так (пакет cpu-checker)
    # https://sources.debian.org/src/cpu-checker/0.7-1.5/kvm-ok
    def get_qemu_parameters(self) -> str:
        if CurrentOs.compat_arch(self.__vm_meta_data.get_arch()):
            if CurrentOs.is_linux():
                return "-accel kvm"
            elif CurrentOs.is_windows_platform():
                return "-accel whpx"

        return "-accel tcg"
