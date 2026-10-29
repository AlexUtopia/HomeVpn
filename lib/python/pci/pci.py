"""PCI устройства: разбор ``lspci``, IOMMU группы и режимы проброса."""

import json
import os
import re
import subprocess
import typing

from lib.python.logger import Logger
from lib.python.types import JsonType, Path
from lib.python.utils import BaseParser, Field, String, UInt8, UInt8Hex, get_all_subclasses
from lib.python.vm import VmMetaData

from lib.python.pci.pci_address import PciAddress
from lib.python.pci.pci_class_code import PciClassCode
from lib.python.pci.pci_passthrough_mode import PciPassthroughMode
from lib.python.pci.pci_vid_pid import PciVidPid


# https://en.wikipedia.org/wiki/PCI_configuration_space
class Pci(BaseParser):
    """PCI устройство

    .. note::
       Поля описываются аннотациями :class:`~lib.python.utils.base_parser.Field`;
       ``iommu_group`` по умолчанию ``None``, так как ``0`` — валидный номер
       IOMMU группы.
    """
    # https://github.com/pciutils/pciutils/blob/master/ls-caps.c#L1457
    class PciExpressCapability(int):
        """Наличие PCI Express capability (0/1)"""

        def __new__(cls, value: typing.Any = 0) -> typing.Self:
            """Создать признак наличия capability

            :param value: Любое значение; истинность преобразуется в 0 или 1
            :return: Признак наличия capability
            """
            return super().__new__(cls, int(bool(value)))

        @staticmethod
        def get_regex() -> str:
            """Получить регулярное выражение capability

            :return: Регулярное выражение
            """
            return r"Capabilities: \[[0-9A-Fa-f]{2}\] Express"

    # https://github.com/pciutils/pciutils/blob/master/ls-ecaps.c#L266
    class AcsCapability(int):
        """Наличие ACS capability (0/1)"""

        def __new__(cls, value: typing.Any = 0) -> typing.Self:
            """Создать признак наличия capability

            :param value: Любое значение; истинность преобразуется в 0 или 1
            :return: Признак наличия capability
            """
            return super().__new__(cls, int(bool(value)))

        @staticmethod
        def get_regex() -> str:
            """Получить регулярное выражение capability

            :return: Регулярное выражение
            """
            return r"Capabilities: \[[0-9A-Fa-f]{3} v\d+\] Access Control Services"

    # https://github.com/pciutils/pciutils/blob/master/ls-ecaps.c#L381
    class SriovCapability(int):
        """Наличие SR-IOV capability (0/1)"""

        def __new__(cls, value: typing.Any = 0) -> typing.Self:
            """Создать признак наличия capability

            :param value: Любое значение; истинность преобразуется в 0 или 1
            :return: Признак наличия capability
            """
            return super().__new__(cls, int(bool(value)))

        @staticmethod
        def get_regex() -> str:
            """Получить регулярное выражение capability

            :return: Регулярное выражение
            """
            return r"Capabilities: \[[0-9A-Fa-f]{3} v\d+\] Single Root I\/O Virtualization \(SR-IOV\)"

    address: typing.Annotated[PciAddress, Field()]
    class_name: typing.Annotated[String, Field()]
    class_code: typing.Annotated[PciClassCode, Field()]
    device_name: typing.Annotated[String, Field()]
    device_id: typing.Annotated[PciVidPid, Field()]
    revision: typing.Annotated[UInt8Hex, Field()]
    prog_if: typing.Annotated[UInt8Hex, Field()]
    subsystem_name: typing.Annotated[String, Field()]
    subsystem_id: typing.Annotated[PciVidPid, Field()]
    # 0 - валидный номер IOMMU группы, поэтому None означает "группа неизвестна"
    iommu_group: typing.Annotated[UInt8 | None, Field(default=None)]
    kernel_module: typing.Annotated[String, Field()]
    is_pci_express: typing.Annotated[PciExpressCapability, Field()]
    is_acs: typing.Annotated[AcsCapability, Field()]
    is_sriov: typing.Annotated[SriovCapability, Field()]

    # https://pkgs.org/search/?q=pciutils
    # https://man7.org/linux/man-pages/man8/lspci.8.html
    __CMD_LINE = "lspci -nnk -vvv -D"

    def __init__(self) -> None:
        """Создать PCI устройство со значениями полей по умолчанию"""
        super().__init__()

    def __eq__(self, other: object) -> bool:
        """Сравнить устройства по адресу и идентификатору

        :param other: Другое устройство
        :return: ``True`` — устройства совпадают
        """
        if other is self:
            return True
        if isinstance(other, Pci):
            return self.get_address_and_id() == other.get_address_and_id()
        return False

    def __hash__(self) -> int:
        """Хеш устройства по адресу и идентификатору

        :return: Хеш
        """
        return hash(self.get_address_and_id())

    def get_short_description(self, indent_spaces_count: int = 0) -> str:
        """Получить краткое описание устройства

        :param indent_spaces_count: Количество пробелов в начале строки
        :return: Описание вида ``[адрес_идентификатор] (класс) имя устройства``
        """
        return f"{' ' * indent_spaces_count}[{self.get_address_and_id()}] ({self.class_name}) {self.device_name}"

    def _init(self, pci: typing.Any) -> None:
        """Инициализировать устройство из другого устройства или словаря

        :param pci: Источник значений
        """
        self.copy_if(pci)

    @staticmethod
    def from_string(model: str) -> "Pci":
        """Создать устройство из JSON-строки

        :param model: JSON-строка
        :return: PCI устройство
        """
        return Pci.from_json(json.loads(model))

    @staticmethod
    def from_json(model: JsonType) -> "Pci":
        """Создать устройство из JSON-объекта

        :param model: JSON-объект с полями устройства
        :return: PCI устройство (при необходимости — экземпляр подкласса)
        :raises ValueError: Модель не является JSON-объектом
        """
        if not isinstance(model, dict):
            raise ValueError(f"[Pci] JSON object expected: {model}")

        result = Pci()
        for key, value in model.items():
            result[key] = value
        return Pci.__build(result)

    def get_id(self) -> PciVidPid:
        """Получить идентификатор устройства (VID:PID)

        :return: Идентификатор устройства
        """
        return self.device_id

    def get_address_and_id(self) -> str:
        """Получить адрес и идентификатор устройства

        :return: Строка вида ``адрес_VID:PID``
        """
        return f"{self.address}_{self.get_id()}"

    def get_kernel_parameters(self) -> list[dict[str, typing.Any]]:
        """Получить параметры ядра хоста для устройства

        :return: Список параметров ядра
        """
        return [{"module_blacklist": self.kernel_module}]

    def get_vfio_pci_options_table(self, _vm_meta_data: VmMetaData) -> tuple[
            dict[str, typing.Any], list[dict[str, typing.Any]]]:
        """Получить параметры устройства ``vfio-pci`` и дополнительные параметры QEMU

        :param _vm_meta_data: Метаданные виртуальной машины (не используются)
        :return: Кортеж из параметров устройства ``vfio-pci`` и дополнительных
                 параметров QEMU, которые добавляются вне блока ``-device``

        .. note::
           Параметр ``host`` (адрес PCI устройства) добавляет
           :class:`VfioPci`, а не сам PCI класс
        """
        return {"multifunction": "on"}, []

    def get_qemu_parameters(self, _vm_meta_data: VmMetaData) -> list[dict[str, typing.Any]]:
        """Получить дополнительные параметры QEMU для PCI устройства

        :param _vm_meta_data: Метаданные виртуальной машины (не используются)
        :return: Список дополнительных параметров QEMU

        .. note::
           По умолчанию устройство не добавляет параметров. Параметры,
           зависящие от режима проброса, устройство возвращает вторым
           элементом кортежа из :meth:`get_vfio_pci_options_table`
        """
        return []

    # https://www.intel.com/content/www/us/en/docs/graphics-for-linux/developer-reference/1-0/dump-video-bios.html
    # https://stackoverflow.com/a/52174005
    def get_rom(self, dir_path_for_save_rom_file: str | os.PathLike[str]) -> Path:
        """Извлечь ROM устройства в файл

        :param dir_path_for_save_rom_file: Каталог для сохранения ROM
        :return: Путь до файла ROM
        """
        result = Path(dir_path_for_save_rom_file) / self.get_rom_file_name()

        rom_file_path = self.__get_sysfs_pci_device_path() / "rom"
        if not rom_file_path.file_exists():
            Logger.instance().warning("[PCI/%s] ROM NOT FOUND: %s", self.address, rom_file_path)
            return result

        rom_file_path.write_text("1")

        result.parent.makedirs()
        result.copy_from(rom_file_path)

        rom_file_path.write_text("0")

        return result

    def is_boot_vga(self) -> bool:
        """Проверить, является ли устройство загрузочным VGA

        :return: ``True`` — устройство используется для вывода при загрузке
        """
        is_boot_vga_path = self.__get_sysfs_pci_device_path() / "boot_vga"
        if not is_boot_vga_path.exists():
            return False
        return bool(int(is_boot_vga_path.read_text()))

    # NB: заменить : на другой символ, имя файла используется в путях Windows
    def get_rom_file_name(self) -> str:
        """Получить имя файла ROM

        :return: Имя файла ROM
        """
        return f"{self.get_address_and_id()}_rom.bin"

    def __get_sysfs_pci_device_path(self) -> Path:
        """Получить путь до устройства в sysfs

        :return: Путь ``/sys/bus/pci/devices/<адрес>``
        """
        return Path(f"/sys/bus/pci/devices/{self.address}")

    def is_capabilities(self, is_pci_express: bool | None = None, is_acs: bool | None = None,
                        is_sriov: bool | None = None) -> bool:
        """Проверить capabilities устройства

        :param is_pci_express: Ожидаемое наличие PCI Express capability; ``None`` — не проверять
        :param is_acs: Ожидаемое наличие ACS capability; ``None`` — не проверять
        :param is_sriov: Ожидаемое наличие SR-IOV capability; ``None`` — не проверять
        :return: ``True`` — все заданные условия выполнены
        """
        table: dict[str, bool | None] = {"is_pci_express": is_pci_express,
                                         "is_acs": is_acs,
                                         "is_sriov": is_sriov}

        for key, value in table.items():
            if value is not None and bool(value) != bool(self[key]):
                return False
        return True

    class PciList(set["Pci"]):
        """Список PCI устройств"""

        def __str__(self) -> str:
            """Сериализовать список в JSON

            :return: JSON-представление списка
            """
            return json.dumps(list(self), default=lambda o: o.get_fields_as_dict())

        def __repr__(self) -> str:
            """Сериализовать список в JSON

            :return: JSON-представление списка
            """
            return self.__str__()

        def get_short_description(self, pci_list_other: "Pci.PciList", indent_spaces_count: int = 0) -> str:
            """Получить краткое описание списка относительно другого списка

            :param pci_list_other: Список для сравнения
            :param indent_spaces_count: Количество пробелов в начале строки
            :return: Описание пересечения и разницы списков
            """
            intersection = "\n".join([pci.get_short_description(indent_spaces_count=indent_spaces_count) for pci in
                                      self.intersection(pci_list_other)])
            if intersection:
                intersection = f"\n{intersection}"

            difference = "\n".join([pci.get_short_description(indent_spaces_count=indent_spaces_count) for pci in
                                    self.difference(pci_list_other)])
            if difference:
                difference = f"\n{difference}"

            indent = ' ' * int(indent_spaces_count / 2)
            return f"{indent}For passthrough:{intersection}\n{indent}Other:{difference}"

        @staticmethod
        def from_string(model: str) -> "Pci.PciList":
            """Создать список из JSON-строки

            :param model: JSON-строка
            :return: Список PCI устройств
            """
            return Pci.PciList.from_json(json.loads(model))

        @staticmethod
        def from_json(model: JsonType) -> "Pci.PciList":
            """Создать список из JSON-объекта

            :param model: JSON-массив с устройствами
            :return: Список PCI устройств
            :raises ValueError: Модель не является JSON-массивом
            """
            if not isinstance(model, list):
                raise ValueError(f"[PciList] JSON array expected: {model}")

            result = Pci.PciList()
            for item in model:
                result.add(Pci.from_json(item))
            return result

        def is_vfio_pci_applied(self) -> bool:
            """Проверить, что хотя бы одно устройство использует драйвер ``vfio-pci``

            :return: ``True`` — драйвер ``vfio-pci`` применён
            """
            for pci in self:
                if pci.kernel_module == "vfio-pci":
                    return True
            return False

        def is_iommu_enabled(self) -> bool:
            """Проверить, что все устройства входят в IOMMU группы

            :return: ``True`` — у всех устройств известна IOMMU группа
            """
            return len(self.get_iommu_group_list()) == len(self)

        def get_iommu_group_set(self) -> set[UInt8]:
            """Получить множество IOMMU групп устройств

            :return: Множество известных IOMMU групп
            """
            result: set[UInt8] = set()
            for pci in self:
                if pci.iommu_group is not None:
                    result.add(pci.iommu_group)
            return result

        def get_iommu_group_list(self) -> list[UInt8]:
            """Получить список IOMMU групп устройств

            :return: Список известных IOMMU групп
            """
            result: list[UInt8] = []
            for pci in self:
                if pci.iommu_group is not None:
                    result.append(pci.iommu_group)
            return result

        def get_pci_table_by_iommu_group(self) -> dict[UInt8 | None, "Pci.PciList"]:
            """Сгруппировать устройства по IOMMU группам

            :return: Словарь ``{IOMMU группа: устройства}``; устройства без группы попадают в ключ ``None``
            """
            result: dict[UInt8 | None, Pci.PciList] = {}
            for pci in self:
                if pci.iommu_group in result:
                    result[pci.iommu_group].add(pci)
                else:
                    result[pci.iommu_group] = Pci.PciList([pci])
            return result

        def get_pci_list_by_iommu_group(self, iommu_group: UInt8 | None) -> "Pci.PciList":
            """Получить устройства IOMMU группы

            :param iommu_group: Номер IOMMU группы
            :return: Список устройств группы
            """
            pci_table_by_iommu_group = self.get_pci_table_by_iommu_group()
            if iommu_group in pci_table_by_iommu_group:
                return pci_table_by_iommu_group[iommu_group]
            return Pci.PciList()

        def get_vga_list(self, mode: PciPassthroughMode = PciPassthroughMode.DEFAULT,
                         vga_audio_passthrough_mode: PciPassthroughMode = PciPassthroughMode.NONE) -> "Pci.PciList":
            """Получить VGA устройства и связанные с ними аудиоустройства

            :param mode: Режим проброса VGA устройств
            :param vga_audio_passthrough_mode: Режим проброса аудиоустройств HDMI
            :return: Список устройств
            """
            result = Pci.PciList()
            for pci in self:
                if pci.class_code.is_vga():
                    result.add(pci)

            vga_audio_list = self.get_vga_audio_list(result, mode=vga_audio_passthrough_mode)
            result = self.get_passedthrough(result, mode=mode)
            result.update(vga_audio_list)
            return result

        def get_vga_audio_list(self, pci_vga_list: "Pci.PciList",
                               mode: PciPassthroughMode = PciPassthroughMode.DEFAULT) -> "Pci.PciList":
            """Получить аудиоустройства HDMI для VGA устройств

            :param pci_vga_list: Список VGA устройств
            :param mode: Режим проброса аудиоустройств
            :return: Список аудиоустройств
            """
            result = Pci.PciList()
            for pci in pci_vga_list:
                result.update(self.get_audio_list(subsystem_id=pci.subsystem_id, mode=mode))
            return result

        def get_audio_list(self, subsystem_id: PciVidPid | None = None,
                           mode: PciPassthroughMode = PciPassthroughMode.DEFAULT) -> "Pci.PciList":
            """Получить аудиоустройства

            :param subsystem_id: Идентификатор subsystem устройства; ``None`` — все аудиоустройства
            :param mode: Режим проброса
            :return: Список аудиоустройств
            """
            result = Pci.PciList()
            for pci in self:
                if pci.class_code.is_audio():
                    if not subsystem_id:
                        result.add(pci)
                    elif subsystem_id == pci.subsystem_id:
                        result.add(pci)
            return self.get_passedthrough(result, mode=mode)

        def get_usb_host_list(self, mode: PciPassthroughMode = PciPassthroughMode.DEFAULT) -> "Pci.PciList":
            """Получить USB контроллеры

            :param mode: Режим проброса
            :return: Список USB контроллеров
            """
            result = Pci.PciList()
            for pci in self:
                if pci.class_code.is_usb_host_controller(pci.prog_if):
                    result.add(pci)
            return self.get_passedthrough(result, mode=mode)

        def get_isa_bridge_list(self, mode: PciPassthroughMode = PciPassthroughMode.DEFAULT) -> "Pci.PciList":
            """Получить ISA мосты

            :param mode: Режим проброса
            :return: Список ISA мостов
            """
            result = Pci.PciList()
            for pci in self:
                if pci.class_code.is_isa_bridge():
                    result.add(pci)
            return self.get_passedthrough(result, mode=mode)

        def get_pci_list_by_capabilities(self, is_pci_express: bool | None = None, is_acs: bool | None = None,
                                         is_sriov: bool | None = None) -> "Pci.PciList":
            """Получить устройства с заданными capabilities

            :param is_pci_express: Ожидаемое наличие PCI Express capability; ``None`` — не проверять
            :param is_acs: Ожидаемое наличие ACS capability; ``None`` — не проверять
            :param is_sriov: Ожидаемое наличие SR-IOV capability; ``None`` — не проверять
            :return: Список устройств
            """
            result = Pci.PciList()
            for pci in self:
                if pci.is_capabilities(is_pci_express=is_pci_express, is_acs=is_acs, is_sriov=is_sriov):
                    result.add(pci)
            return result

        def is_each_device_in_its_own_iommu_group(self, pci_list_for_checking: "Pci.PciList") -> bool:
            """Проверить, что каждая IOMMU группа содержит только целевые устройства

            :param pci_list_for_checking: Проверяемый список устройств
            :return: ``True`` — каждая IOMMU группа состоит только из проверяемых устройств
            """
            pci_table_by_iommu_group = self.get_pci_table_by_iommu_group()

            for iommu_group, pci_list in pci_list_for_checking.get_pci_table_by_iommu_group().items():
                if iommu_group in pci_table_by_iommu_group:
                    if len(pci_table_by_iommu_group[iommu_group]) != len(pci_list):
                        return False
            return True

        # Сравнение производится относительно self
        def check_iommu_group_for_passthrough(self, pci_list_for_checking: "Pci.PciList") -> bool | None:
            """Проверить IOMMU группы пробрасываемых PCI устройств

            :param pci_list_for_checking: Список PCI устройств для проверки
            :return: ``True`` — можно пробросить без ограничений, ``False`` — можно пробросить
                     с ACS override patch, ``None`` — пробросить нельзя
            """
            pci_table_by_iommu_group = self.get_pci_table_by_iommu_group()
            result: bool | None = True
            for iommu_group, pci_list in pci_list_for_checking.get_pci_table_by_iommu_group().items():
                if iommu_group in pci_table_by_iommu_group:
                    pci_list_by_iommu_group = pci_table_by_iommu_group[iommu_group]
                    if len(pci_list_by_iommu_group) != len(pci_list):
                        if len(pci_list.get_pci_list_by_capabilities(is_pci_express=True, is_acs=False)) != len(
                                pci_list):
                            # ACS override patch применим к PCI Express устройству без capability ACS
                            # https://github.com/benbaker76/linux-acs-override/blob/main/6.3/acso.patch#L101
                            result = None
                            Logger.instance().warning("[-] IOMMU group %s will NOT be passedthrough completely:\n%s\n",
                                                      iommu_group,
                                                      pci_list_by_iommu_group.get_short_description(
                                                          indent_spaces_count=4, pci_list_other=pci_list))
                        else:
                            if result is not None:
                                result = False
                            Logger.instance().info(
                                "[o] IOMMU group %s will be passedthrough completely if ASC override applicable:\n%s\n",
                                iommu_group,
                                pci_list_by_iommu_group.get_short_description(indent_spaces_count=4,
                                                                              pci_list_other=pci_list))
                    else:
                        Logger.instance().info("[+] IOMMU group %s will be passedthrough completely:\n%s\n",
                                               iommu_group,
                                               pci_list_by_iommu_group.get_short_description(
                                                   indent_spaces_count=4, pci_list_other=pci_list_by_iommu_group))
            return result

        def get_passedthrough(self, target_pci_list: "Pci.PciList",
                              mode: PciPassthroughMode | int = PciPassthroughMode.DEFAULT) -> "Pci.PciList":
            """Отфильтровать устройства по режиму проброса

            :param target_pci_list: Целевые устройства
            :param mode: Режим проброса
            :return: Список устройств, которые нужно пробросить
            """
            if not isinstance(mode, PciPassthroughMode):
                mode = PciPassthroughMode(mode)
            if mode.is_none():
                return Pci.PciList()

            if mode.is_default():
                return target_pci_list

            result = Pci.PciList()
            pci_table_by_iommu_group = self.get_pci_table_by_iommu_group()
            for iommu_group, pci_list in target_pci_list.get_pci_table_by_iommu_group().items():
                if iommu_group in pci_table_by_iommu_group:
                    if mode.is_flex():
                        if len(pci_table_by_iommu_group[iommu_group]) == len(pci_list):
                            result.update(pci_table_by_iommu_group[iommu_group])
                    elif mode.is_force():
                        result.update(pci_table_by_iommu_group[iommu_group])
            return result

        def get_by_address(self, pci_address_list: list[PciAddress]) -> "Pci.PciList":
            """Получить устройства по адресам

            :param pci_address_list: Список адресов
            :return: Список устройств
            """
            result = Pci.PciList()
            for pci in self:
                if pci.address in pci_address_list:
                    result.add(pci)
            return result

        def get_pci_id_list(self) -> list[PciVidPid]:
            """Получить идентификаторы устройств

            :return: Список идентификаторов ``VID:PID``
            """
            return [pci.get_id() for pci in self]

        def to_sorted_list(self) -> list["Pci"]:
            """Получить устройства, отсортированные по адресу

            :return: Список устройств
            """
            result = list(self)
            result.sort(key=lambda pci: pci.address)
            return result

    @staticmethod
    def get_list(lspci_output_mock: str | None = None) -> "Pci.PciList":
        """Получить список PCI устройств

        :param lspci_output_mock: Вывод ``lspci`` для разбора; ``None`` — запустить ``lspci``
        :return: Список PCI устройств
        """
        result = Pci.PciList()

        lspci_out = lspci_output_mock if lspci_output_mock else Pci.__run_lspci()

        pci: Pci | None = None
        for match in re.finditer(Pci.__get_regex(), lspci_out, flags=re.MULTILINE):
            for key, value in match.groupdict().items():
                if value is not None:
                    if key == "address":
                        if pci is not None:
                            result.add(Pci.__build(pci))
                        pci = Pci()
                    if pci is None:
                        continue
                    pci[key] = value
        return result

    @staticmethod
    def __get_regex() -> str:
        """Собрать регулярное выражение для разбора вывода ``lspci``

        :return: Регулярное выражение с именованными группами полей
        """
        tmp = Pci()
        result = ""
        result += fr"{tmp.get_regex_for('address')} "
        result += fr"{tmp.get_regex_for('class_name')} "
        result += fr"\[{tmp.get_regex_for('class_code')}\]: "
        result += fr"{tmp.get_regex_for('device_name')} "
        result += fr"\[{tmp.get_regex_for('device_id')}\]"
        result += fr"(?> \(rev {tmp.get_regex_for('revision')}\))?"
        result += fr"(?> \(prog-if {tmp.get_regex_for('prog_if')} \[.*\]\))?"
        result += "|"
        result += fr"Subsystem: {tmp.get_regex_for('subsystem_name')} "
        result += fr"\[{tmp.get_regex_for('subsystem_id')}\]"
        result += "|"
        result += fr"IOMMU group: {tmp.get_regex_for('iommu_group')}"
        result += "|"
        result += fr"Kernel driver in use: {tmp.get_regex_for('kernel_module')}"
        result += "|"
        result += fr"{tmp.get_regex_for('is_pci_express')}"
        result += "|"
        result += fr"{tmp.get_regex_for('is_acs')}"
        result += "|"
        result += fr"{tmp.get_regex_for('is_sriov')}"
        return result

    @staticmethod
    def __build(base_pci: "Pci") -> "Pci":
        """Создать устройство нужного подкласса

        :param base_pci: Разобранное устройство
        :return: Экземпляр первого подходящего подкласса или ``base_pci``
        """
        for sub_cls in get_all_subclasses(Pci):
            if sub_cls.is_my_instance(base_pci):
                return typing.cast(Pci, sub_cls(base_pci))
        return base_pci

    @staticmethod
    def __run_lspci() -> str:
        """Запустить ``lspci``

        :return: Вывод ``lspci`` или пустая строка при ошибке
        """
        cmd_result = subprocess.run(Pci.__CMD_LINE, shell=True, capture_output=True, text=True, check=False)
        if cmd_result.returncode:
            return ""
        return cmd_result.stdout
