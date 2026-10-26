from __future__ import annotations

import pathlib

from .pci import Pci
from .intel_integrated_vga_generation import IntelIntegratedVgaGeneration


# https://gitlab.com/qemu-project/qemu/-/blob/master/hw/vfio/igd.c
# https://gitlab.com/qemu-project/qemu/-/blob/master/docs/igd-assign.txt
class IntelIntegratedVgaStolenMemorySize:
    """Размер Data Stolen Memory (DSM) встроенной графики Intel

    Класс читает регистр GGC (Graphics Control Register) HostBridge и разбирает
    поле GMS (Graphics Mode Select) сообразно поколению GPU. Значение GMS — это
    именно то, что передаётся в параметре QEMU ``x-igd-gms``

    .. note::
       Адрес HostBridge фиксирован (``0000:00:00.0``). На серверных платформах
       может быть несколько HostBridge, но CPU Intel со встроенным GPU на таких
       платформах не бывает, поэтому выбор адреса однозначен

    .. note::
       Чтение PCI config space за пределами первых ``0x40`` байт требует прав
       root: sysfs отдаёт регистр GGC (offset ``0x50``) только привилегированному
       пользователю

    .. seealso::
       - https://gitlab.com/qemu-project/qemu/-/blob/master/hw/vfio/igd.c
       - https://gitlab.com/qemu-project/qemu/-/blob/master/docs/igd-assign.txt
    """

    HOST_BRIDGE_PCI_ADDRESS = "0000:00:00.0"

    GGC_OFFSET = 0x50  # Graphics Control Register (GMCH)
    GGC_SIZE = 4

    GMS_SHIFT_LEGACY = 3  # SNB_GMCH в i915 (Intel CPU Sandy Bridge - Haswell)
    GMS_MASK_LEGACY = 0x1f

    GMS_SHIFT = 8  # BDW_GMCH в i915 (Intel CPU Broadwell+)
    GMS_MASK = 0xff

    MIB = 1024 ** 2
    GMS_UNIT_MIB = 32
    GMS_4_MIB_UNIT_MIB = 4
    GMS_UNIT_BYTES = GMS_UNIT_MIB * MIB
    GMS_4_MIB_UNIT_BYTES = GMS_4_MIB_UNIT_MIB * MIB
    GMS_4_MIB_ENCODING_BASE = 0xf0

    def __init__(self, gms: int, size_in_bytes: int):
        self.__gms = gms
        self.__size_in_bytes = size_in_bytes

    def __str__(self):
        return f"GMS={self.__gms:#04x} ({self.get_size_in_mib()} MiB)"

    def __repr__(self):
        return self.__str__()

    @staticmethod
    def get(pci: Pci) -> IntelIntegratedVgaStolenMemorySize:
        """Вычислить размер DSM для переданного IGD

        :param pci: PCI устройство встроенной графики Intel
        :return: Размер Data Stolen Memory
        :raises Exception: Если регистр GGC недоступен для чтения или поколение GPU не известно
        """
        return IntelIntegratedVgaStolenMemorySize.from_ggc(
            IntelIntegratedVgaStolenMemorySize.__read_ggc(), IntelIntegratedVgaGeneration.from_pci(pci))

    @staticmethod
    def from_ggc(ggc: int, generation: IntelIntegratedVgaGeneration) -> IntelIntegratedVgaStolenMemorySize:
        """Вычислить размер DSM по значению регистра GGC

        :param ggc: Значение регистра GGC (Graphics Control Register)
        :param generation: Поколение встроенной графики Intel
        :return: Размер Data Stolen Memory
        :raises Exception: Если для поколения не известен формат регистра GGC
        """
        if not generation.is_stolen_memory_size_supported():
            raise Exception(
                f"[IntelIntegratedVgaStolenMemorySize] DSM size NOT SUPPORTED for GPU \"{generation}\": "
                f"unknown GGC register format")

        gms = IntelIntegratedVgaStolenMemorySize.__extract_gms(ggc, generation)
        size_in_bytes = IntelIntegratedVgaStolenMemorySize.__get_size_in_bytes(gms, generation)
        return IntelIntegratedVgaStolenMemorySize(gms, size_in_bytes)

    def get_gms(self) -> int:
        """Получить значение поля GMS (Graphics Mode Select)

        :return: Значение поля GMS

        .. note::
           Именно это значение принимает QEMU в параметре ``x-igd-gms``
        """
        return self.__gms

    def get_size_in_bytes(self) -> int:
        """Получить размер Data Stolen Memory в байтах

        :return: Размер Data Stolen Memory в байтах
        """
        return self.__size_in_bytes

    def get_size_in_mib(self) -> int:
        """Получить размер Data Stolen Memory в MiB

        :return: Размер Data Stolen Memory в MiB
        """
        return self.__size_in_bytes // self.MIB

    @staticmethod
    def __read_ggc() -> int:
        """Прочитать регистр GGC с HostBridge хоста

        :return: Значение регистра GGC
        :raises Exception: Если файл конфигурации недоступен или прочитано меньше байт, чем нужно
        """
        config_path = pathlib.Path(
            f"/sys/bus/pci/devices/{IntelIntegratedVgaStolenMemorySize.HOST_BRIDGE_PCI_ADDRESS}/config")

        try:
            with config_path.open("rb") as config_file:
                config_file.seek(IntelIntegratedVgaStolenMemorySize.GGC_OFFSET)
                data = config_file.read(IntelIntegratedVgaStolenMemorySize.GGC_SIZE)
        except OSError as error:
            raise Exception(f"[IntelIntegratedVgaStolenMemorySize] Read GGC FAIL: {config_path}: {error}")

        # На чтение PCI config space за пределами первых 0x40 байт нужны права root
        if len(data) != IntelIntegratedVgaStolenMemorySize.GGC_SIZE:
            raise Exception(
                f"[IntelIntegratedVgaStolenMemorySize] Read GGC FAIL: {config_path} "
                f"(offset={IntelIntegratedVgaStolenMemorySize.GGC_OFFSET:#04x}, read={len(data)} bytes). "
                f"Root privileges are required to read PCI config space beyond 0x40")

        return int.from_bytes(data, byteorder="little")

    @staticmethod
    def __extract_gms(ggc: int, generation: IntelIntegratedVgaGeneration) -> int:
        """Извлечь поле GMS из регистра GGC

        :param ggc: Значение регистра GGC
        :param generation: Поколение встроенной графики Intel
        :return: Значение поля GMS
        :raises Exception: Если номер поколения не известен

        .. note::
           До поколения 8 (Broadwell) поле GMS находится в битах 3..7, начиная
           с поколения 8 — в битах 8..15 регистра GGC
        """
        generation_number = generation.get_generation()
        if generation_number is None:
            raise Exception(
                f"[IntelIntegratedVgaStolenMemorySize] GMS extraction FAIL: unknown GPU generation \"{generation}\"")

        if generation_number < 8:
            return (ggc >> IntelIntegratedVgaStolenMemorySize.GMS_SHIFT_LEGACY) & \
                   IntelIntegratedVgaStolenMemorySize.GMS_MASK_LEGACY

        return (ggc >> IntelIntegratedVgaStolenMemorySize.GMS_SHIFT) & \
               IntelIntegratedVgaStolenMemorySize.GMS_MASK

    @staticmethod
    def __get_size_in_bytes(gms: int, generation: IntelIntegratedVgaGeneration) -> int:
        """Перевести значение поля GMS в размер Data Stolen Memory

        :param gms: Значение поля GMS
        :param generation: Поколение встроенной графики Intel
        :return: Размер Data Stolen Memory в байтах
        :raises Exception: Если номер поколения не известен

        .. note::
           До поколения 9 (Skylake) и для значений ``0x00..0xef`` начиная
           с поколения 9 шаг равен 32 MiB, а для значений ``0xf0..0xfe`` —
           4 MiB (начиная с 4 MiB). Значение ``0xff`` не определено
        """
        generation_number = generation.get_generation()
        if generation_number is None:
            raise Exception(
                f"[IntelIntegratedVgaStolenMemorySize] DSM size calculation FAIL: "
                f"unknown GPU generation \"{generation}\"")

        if generation_number < 9 or gms < IntelIntegratedVgaStolenMemorySize.GMS_4_MIB_ENCODING_BASE:
            return gms * IntelIntegratedVgaStolenMemorySize.GMS_UNIT_BYTES

        return (gms - IntelIntegratedVgaStolenMemorySize.GMS_4_MIB_ENCODING_BASE + 1) * \
               IntelIntegratedVgaStolenMemorySize.GMS_4_MIB_UNIT_BYTES
