from __future__ import annotations

import enum

from .pci import Pci
from .pci_vid_pid import PciVidPid


_SANDY_BRIDGE_PID_SET = {0x0102, 0x0106, 0x010A, 0x0112, 0x0116, 0x0122, 0x0126}
_IVY_BRIDGE_PID_SET = {0x0152, 0x0156, 0x015A, 0x0162, 0x0166, 0x016A}
_PRE_BROADWELL_PREFIX_SET = {0x01, 0x04, 0x0A, 0x0C, 0x0D}

_LEGACY_GENERATION_MIN = 6  # Intel CPU Sandy Bridge
_LEGACY_GENERATION_MAX = 9  # Intel CPU Comet Lake


# https://gitlab.com/qemu-project/qemu/-/blob/master/hw/vfio/igd.c#L44
# https://github.com/torvalds/linux/blob/master/include/drm/intel/i915_pciids.h
class IntelIntegratedVgaGeneration(enum.Enum):
    """Поколение встроенной графики (IGD) Intel

    .. note::
       Номера поколений соответствуют ``igd_gen()`` из ``hw/vfio/igd.c`` QEMU,
       а не маркетинговым названиям Intel. Именно от номера поколения зависит
       формат регистра GGC и поддерживаемые режимы проброса

    .. seealso::
       - https://gitlab.com/qemu-project/qemu/-/blob/master/hw/vfio/igd.c
       - https://github.com/torvalds/linux/blob/master/include/drm/intel/i915_pciids.h
    """

    SANDY_BRIDGE = ("Gen6 (Sandy Bridge)", 6, False)
    IVY_BRIDGE = ("Gen7 (Ivy Bridge)", 7, False)
    HASWELL = ("Gen7.5 (Haswell)", 7, False)
    BROADWELL = ("Gen8 (Broadwell)", 8, True)
    SKYLAKE = ("Gen9 (Skylake)", 9, True)
    KABY_LAKE = ("Gen9.5 (Kaby Lake)", 9, True)
    COFFEE_LAKE = ("Gen9.5 (Coffee Lake)", 9, True)
    COMET_LAKE = ("Gen9.5 (Comet Lake)", 9, True)
    ICE_LAKE = ("Gen11 (Ice Lake)", 11, True)
    TIGER_LAKE = ("Gen12 (Tiger Lake)", 12, True)
    ROCKET_LAKE = ("Gen12 (Rocket Lake)", 12, True)
    ALDER_LAKE = ("Intel Xe (Alder Lake / N-series)", 12, True)
    RAPTOR_LAKE = ("Intel Xe (Raptor Lake)", 12, True)
    METEOR_LAKE = ("Intel Xe-LPG / Arc (Meteor & Arrow Lake)", 12, True)
    ARROW_LAKE = ("Intel Xe-LPG+ / Arc (Arrow Lake)", 12, True)
    LUNAR_LAKE = ("Intel Xe2 / Arc (Lunar Lake)", None, True)
    PANTHER_LAKE = ("Intel Xe3 / Arc (Panther Lake)", None, True)
    ARC_ALCHEMIST = ("Intel Arc Discrete (Alchemist)", None, False)
    ARC_BATTLEMAGE = ("Intel Arc Discrete (Battlemage)", None, False)
    UNKNOWN = ("Unknown Intel GPU", None, True)

    def __init__(self, display_name: str, generation: int | None, is_upt_supported: bool):
        self.__display_name = display_name
        self.__generation = generation
        self.__is_upt_supported = is_upt_supported

    def __str__(self) -> str:
        return self.__display_name

    def __repr__(self) -> str:
        return self.__str__()

    def get_generation(self) -> int | None:
        """Получить номер поколения в нумерации QEMU

        :return: Номер поколения или ``None``, если поколение не известно
        """
        return self.__generation

    def is_upt_supported(self) -> bool:
        """Проверить поддержку режима UPT (Universal Pass-Through)

        :return: ``True``, если режим поддерживается; иначе ``False``

        .. note::
           UPT поддерживается начиная с Intel CPU Broadwell (поколение 8)
        """
        return self.__is_upt_supported

    def is_legacy_supported(self) -> bool:
        """Проверить поддержку режима Legacy

        :return: ``True``, если режим поддерживается; иначе ``False``

        .. note::
           Legacy поддерживается для Intel CPU Sandy Bridge to Comet Lake
           (поколения 6..9). Для более новых GPU доступен только UPT
           или режимы с готовым Video BIOS (EFI)
        """
        generation = self.__generation
        return generation is not None and _LEGACY_GENERATION_MIN <= generation <= _LEGACY_GENERATION_MAX

    def is_stolen_memory_size_supported(self) -> bool:
        """Проверить, можно ли вычислить размер Data Stolen Memory

        :return: ``True``, если формат регистра GGC для поколения известен; иначе ``False``

        .. note::
           Размер Data Stolen Memory — это значение, которое передаётся
           в параметре QEMU ``x-igd-gms``. Для устройств с неизвестным
           поколением формат GGC не определён, поэтому вычислить его нельзя
        """
        return self.__generation is not None

    @staticmethod
    def from_pci(pci: Pci) -> IntelIntegratedVgaGeneration:
        """Определить поколение IGD по PCI устройству

        :param pci: PCI устройство, у которого берётся ``device_id``
        :return: Поколение IGD; ``UNKNOWN``, если ``device_id`` не задан
        """
        device_id = pci.device_id
        if device_id is None:
            return IntelIntegratedVgaGeneration.UNKNOWN
        return IntelIntegratedVgaGeneration.from_device_id(device_id)

    @staticmethod
    def from_device_id(device_id: PciVidPid) -> IntelIntegratedVgaGeneration:
        """Определить поколение IGD по PCI Device ID

        :param device_id: PCI VID/PID устройства
        :return: Поколение IGD; ``UNKNOWN``, если префикс Device ID не известен

        .. note::
           Для семейств до Broadwell (Sandy Bridge, Ivy Bridge) поколение
           определяется по полному Device ID, для остальных — по старшему байту
        """
        pid = int(device_id.pid)
        prefix = pid >> 8

        # Семейства до Broadwell строго требуют режим Legacy
        if prefix in _PRE_BROADWELL_PREFIX_SET:
            if pid in _SANDY_BRIDGE_PID_SET:
                return IntelIntegratedVgaGeneration.SANDY_BRIDGE
            if pid in _IVY_BRIDGE_PID_SET:
                return IntelIntegratedVgaGeneration.IVY_BRIDGE
            return IntelIntegratedVgaGeneration.HASWELL

        return _FAMILY_TABLE_BY_PREFIX.get(prefix, IntelIntegratedVgaGeneration.UNKNOWN)


# Таблица определена после класса, т.к. ссылается на его члены
_FAMILY_TABLE_BY_PREFIX = {
    0x16: IntelIntegratedVgaGeneration.BROADWELL,
    0x19: IntelIntegratedVgaGeneration.SKYLAKE,
    0x59: IntelIntegratedVgaGeneration.KABY_LAKE,
    0x3E: IntelIntegratedVgaGeneration.COFFEE_LAKE,
    0x9B: IntelIntegratedVgaGeneration.COMET_LAKE,
    0x8A: IntelIntegratedVgaGeneration.ICE_LAKE,
    0x9A: IntelIntegratedVgaGeneration.TIGER_LAKE,
    0x4C: IntelIntegratedVgaGeneration.ROCKET_LAKE,
    0x46: IntelIntegratedVgaGeneration.ALDER_LAKE,
    0xA7: IntelIntegratedVgaGeneration.RAPTOR_LAKE,
    0x7D: IntelIntegratedVgaGeneration.METEOR_LAKE,
    0xB6: IntelIntegratedVgaGeneration.ARROW_LAKE,
    0x64: IntelIntegratedVgaGeneration.LUNAR_LAKE,
    0xB0: IntelIntegratedVgaGeneration.PANTHER_LAKE,
    0x56: IntelIntegratedVgaGeneration.ARC_ALCHEMIST,
    0xE2: IntelIntegratedVgaGeneration.ARC_BATTLEMAGE,
}
