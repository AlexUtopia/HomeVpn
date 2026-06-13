import cpuinfo
import pathlib


# fixme utopia Необходимо проверять параметры загрузки linux kernel (см. /proc/cmdline)
# Нам нужен парсер командной строки для linux kernel
class Iommu:
    # fixme utopia Вырубить виртуализацию в биос и проверить появится ли
    __IOMMU_SYS_FS_PATH = pathlib.Path("/sys/class/iommu/")

    # проверить что в /etc/default/grub есть intel_iommu=on iommu=pt и в dmesg есть
    # iommu: Default domain type: Passthrough
    def check(self) -> bool:
        return self.__IOMMU_SYS_FS_PATH.exists()

    def is_intel(self) -> bool:
        return self.check() and self.__is_cpu_vendor("intel")

    def is_amd(self) -> bool:
        return self.check() and self.__is_cpu_vendor("amd")

    def is_arm(self) -> bool:
        return self.check() and self.__is_cpu_vendor("arm")

    # https://docs.kernel.org/admin-guide/kernel-parameters.html
    def get_kernel_parameters(self) -> list[dict]:
        if self.is_intel():
            return [{"intel_iommu": "on", "iommu": "pt"}]
        elif self.is_amd():
            return [{"amd_iommu": "on", "iommu": "pt"}]
        return []

    def __is_cpu_vendor(self, cpu_vendor: str) -> bool:
        try:
            return str(cpu_vendor) in str(cpuinfo.get_cpu_info()['vendor_id_raw']).lower()
        except Exception:
            return False