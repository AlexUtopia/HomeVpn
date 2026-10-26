from __future__ import annotations

import typing

from lib.python.types import JsonType

from lib.python.pci import Pci, PciVidPid
from lib.python.vm import VmMetaData


class VfioPci:
    def __init__(self, pci_list: Pci.PciList):
        self.__pci_list = pci_list

    def __str__(self):
        return str(self.__pci_list)

    def __repr__(self):
        return self.__str__()

    @staticmethod
    def from_string(model: str) -> VfioPci:
        return VfioPci(Pci.PciList.from_string(model))

    @staticmethod
    def from_json(model: JsonType) -> VfioPci:
        return VfioPci(Pci.PciList.from_json(model))

    def get_pci_list(self) -> Pci.PciList:
        return self.__pci_list

    def get_pci_id_list(self) -> list[PciVidPid]:
        return self.__pci_list.get_pci_id_list()

    def get_kernel_parameters(self) -> list[dict]:
        if len(self.__pci_list) == 0:
            return []

        result = [{"vfio_pci.ids": self.get_pci_id_list()}]

        for pci in self.__pci_list:
            result.extend(pci.get_kernel_parameters())
        return result

    def get_qemu_parameters(self, vm_meta_data: VmMetaData) -> list[dict[str, typing.Any]]:
        """Получить параметры QEMU для пробрасываемых PCI устройств

        :param vm_meta_data: Метаданные виртуальной машины
        :return: Список параметров QEMU

        .. note::
           Параметры устройства формируются только для устройств, включённых
           в IOMMU группу. Дополнительные параметры режима проброса (например,
           ``-vga none``) добавляются сразу после соответствующего ``-device``
        """
        result = []
        for pci in self.__pci_list:
            result.extend(self.__get_device_for_passthrough(pci, vm_meta_data))
            result.extend(pci.get_qemu_parameters(vm_meta_data))
        return result

    @staticmethod
    def __get_device_for_passthrough(pci: Pci, vm_meta_data: VmMetaData) -> list[dict[str, typing.Any]]:
        """Получить параметры QEMU для одного пробрасываемого PCI устройства

        :param pci: PCI устройство
        :param vm_meta_data: Метаданные виртуальной машины
        :return: Список параметров QEMU (``-device vfio-pci`` и дополнительные параметры)

        .. note::
           PCI устройство нельзя пробросить, если оно не включено в IOMMU группу:
           в этом случае список параметров пуст
        """
        if pci.iommu_group is None:
            return []

        vfio_pci_options_table, qemu_parameters = pci.get_vfio_pci_options_table(vm_meta_data)
        vfio_pci_options_table = {"host": pci.address, **vfio_pci_options_table}
        return [{"-device": {"vfio-pci": vfio_pci_options_table}}, *qemu_parameters]
