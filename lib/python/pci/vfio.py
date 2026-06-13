from lib.python.iommu import Iommu
from lib.python.pci import VfioPci


# https://docs.kernel.org/driver-api/vfio-mediated-device.html
# https://docs.kernel.org/driver-api/vfio.html
class Vfio:
    def __init__(self, vfio_pci: VfioPci, iommu: Iommu = Iommu(), is_acs_override: bool = False):
        self.__vfio_pci = vfio_pci
        self.__iommu = iommu
        self.__is_acs_override = is_acs_override

    def get_kernel_parameters(self) -> list[dict]:
        result = [{"modules_load": ["vfio", "vfio_pci", "vfio_iommu_type1", "vfio_virqfd"], "kvm.ignore_msrs": "1",
                   "vfio_io_iommu_type1.allow_unsafe_interrupts": "1"}]
        result.extend(self.__vfio_pci.get_kernel_parameters())
        result.extend(self.__iommu.get_kernel_parameters())
        pci_id_list = self.__vfio_pci.get_pci_id_list()
        # fixme utopia Не более 16-ти устройств, нужно разобраться с опциями downstream и multifunction
        #   Может переопределять только устройства конкретных (целевых) iommu групп а не всё подряд?
        #   https://github.com/zen-kernel/zen-kernel/blob/7.0/main/drivers/pci/quirks.c#L3762
        if self.__is_acs_override and len(pci_id_list) > 0:
            result.append({"pcie_acs_override": [{"id": pci_id_list}]})
        return result
