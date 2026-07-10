import json
import os
import re
import subprocess

from lib.python.logger import Logger
from lib.python.types import Path
from lib.python.utils import BaseParser, String, UInt8, UInt8Hex, get_all_subclasses

from lib.python.pci import PciAddress, PciClassCode, PciPassthroughMode, PciVidPid


# https://en.wikipedia.org/wiki/PCI_configuration_space
class Pci(BaseParser):
    # https://github.com/pciutils/pciutils/blob/master/ls-caps.c#L1457
    class PciExpressCapability(int):
        def __new__(cls, value=0):
            return super(Pci.PciExpressCapability, cls).__new__(cls, int(bool(value)))

        @staticmethod
        def get_regex():
            return r"Capabilities: \[[0-9A-Fa-f]{2}\] Express"

    # https://github.com/pciutils/pciutils/blob/master/ls-ecaps.c#L266
    class AcsCapability(int):
        def __new__(cls, value=0):
            return super(Pci.AcsCapability, cls).__new__(cls, int(bool(value)))

        @staticmethod
        def get_regex():
            return r"Capabilities: \[[0-9A-Fa-f]{3} v\d+\] Access Control Services"

    # https://github.com/pciutils/pciutils/blob/master/ls-ecaps.c#L381
    class SriovCapability(int):
        def __new__(cls, value=0):
            return super(Pci.SriovCapability, cls).__new__(cls, int(bool(value)))

        @staticmethod
        def get_regex():
            return r"Capabilities: \[[0-9A-Fa-f]{3} v\d+\] Single Root I\/O Virtualization \(SR-IOV\)"

    __ADDRESS = "address"
    __CLASS_NAME = "class_name"
    __CLASS_CODE = "class_code"
    __DEVICE_NAME = "device_name"
    __DEVICE_ID = "device_id"
    __REVISION = "revision"
    __PROG_IF = "prog_if"
    __SUBSYSTEM_NAME = "subsystem_name"
    __SUBSYSTEM_ID = "subsystem_id"
    __IOMMU_GROUP = "iommu_group"
    __KERNEL_MODULE = "kernel_module"
    __IS_PCI_EXPRESS = "is_pci_express"
    __IS_ACS = "is_acs"
    __IS_SRIOV = "is_sriov"

    __TABLE = {__ADDRESS: {"type": PciAddress},
               __CLASS_NAME: {"type": String},
               __CLASS_CODE: {"type": PciClassCode},
               __DEVICE_NAME: {"type": String},
               __DEVICE_ID: {"type": PciVidPid},
               __REVISION: {"type": UInt8Hex},
               __PROG_IF: {"type": UInt8Hex},
               __SUBSYSTEM_NAME: {"type": String},
               __SUBSYSTEM_ID: {"type": PciVidPid},
               __IOMMU_GROUP: {"type": UInt8, "default": None},
               __KERNEL_MODULE: {"type": String},
               __IS_PCI_EXPRESS: {"type": PciExpressCapability},
               __IS_ACS: {"type": AcsCapability},
               __IS_SRIOV: {"type": SriovCapability}
               }

    # https://pkgs.org/search/?q=pciutils
    # https://man7.org/linux/man-pages/man8/lspci.8.html
    __CMD_LINE = "lspci -nnk -vvv -D"

    def __init__(self):
        super(Pci, self).__init__(self.__TABLE)

    def __eq__(self, other):
        if other is self:
            return True
        elif isinstance(other, Pci):
            return self.get_address_and_id() == other.get_address_and_id()
        else:
            return False

    def __hash__(self):
        return self.get_address_and_id().__hash__()

    def get_short_description(self, indent_spaces_count=0):
        return f"{' ' * indent_spaces_count}[{self.get_address_and_id()}] ({self.class_name}) {self.device_name}"

    def _init(self, pci):
        self.copy_if(pci)

    @staticmethod
    def from_string(model):
        Pci.from_json(json.loads(model))

    @staticmethod
    def from_json(model):
        result = Pci()
        for key, value in model.items():
            result[key] = value
        return Pci.__build(result)

    def get_id(self) -> PciVidPid:
        return self.device_id

    def get_address_and_id(self) -> str:
        return f"{self.address}_{self.get_id()}"

    def get_kernel_parameters(self):
        return [{"module_blacklist": self.kernel_module}]

    def get_vfio_pci_options_table(self, vm_meta_data):
        return {"multifunction": "on"}

    def get_qemu_parameters(self, vm_meta_data):
        return [VfioPci.get_device_for_passthrough(self, vm_meta_data)]

    def is_other_vga_disable(self):
        return False

    def check_platform(self, qemu_platform):
        pass

    # https://www.intel.com/content/www/us/en/docs/graphics-for-linux/developer-reference/1-0/dump-video-bios.html
    # https://stackoverflow.com/a/52174005
    def get_rom(self, dir_path_for_save_rom_file: str | os.PathLike[str]) -> Path:
        result = Path(dir_path_for_save_rom_file) / self.get_rom_file_name()

        rom_file_path = self.__get_sysfs_pci_device_path() / "rom"
        if not rom_file_path.file_exists():
            Logger.instance().warning(f"[PCI/{self.address}] ROM NOT FOUND: {rom_file_path}")
            return result

        rom_file_path.write_text("1")

        result.parent.makedirs()
        result.copy_from(rom_file_path)

        rom_file_path.write_text("0")

        return result

    def is_boot_vga(self):
        is_boot_vga_path = self.__get_sysfs_pci_device_path() / "boot_vga"
        if not is_boot_vga_path.exists():
            return False
        return bool(int(is_boot_vga_path.read_text()))

    # fixme utopia заменить : на другой символ
    def get_rom_file_name(self) -> str:
        return f"{self.get_address_and_id()}_rom.bin"

    def __get_sysfs_pci_device_path(self) -> Path:
        return Path(f"/sys/bus/pci/devices/{self.address}")

    def is_pci_express(self):
        return self.is_capabilities(is_pci_express=True)

    def is_capabilities(self, is_pci_express=None, is_acs=None, is_sriov=None):
        table = {self.__IS_PCI_EXPRESS: is_pci_express, self.__IS_ACS: is_acs, self.__IS_SRIOV: is_sriov}

        for key, value in table.items():
            if value is not None:
                if bool(value) != bool(self[key]):
                    return False
        return True

    class PciList(set):

        def __str__(self):
            return json.dumps(list(self), default=lambda o: o.get_fields_as_dict())

        def __repr__(self):
            return self.__str__()

        def get_short_description(self, pci_list_other, indent_spaces_count=0):
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
        def from_string(model):
            return Pci.PciList.from_json(json.loads(model))

        @staticmethod
        def from_json(model):
            result = Pci.PciList()
            for item in model:
                result.add(Pci.from_json(item))
            return result

        def is_vfio_pci_applied(self):
            for pci in self:
                if pci.kernel_module and pci.kernel_module == "vfio-pci":
                    return True
            return False

        def is_iommu_enabled(self):
            return len(self.get_iommu_group_list()) == len(self)

        def get_iommu_group_set(self):
            result = set()
            for pci in self:
                if pci.iommu_group is not None:
                    result.add(pci.iommu_group)
            return result

        def get_iommu_group_list(self):
            result = list()
            for pci in self:
                if pci.iommu_group is not None:
                    result.append(pci.iommu_group)
            return result

        def get_pci_table_by_iommu_group(self):
            result = {}
            for pci in self:
                if pci.iommu_group in result:
                    result[pci.iommu_group].add(pci)
                else:
                    result[pci.iommu_group] = Pci.PciList([pci])
            return result

        def get_pci_list_by_iommu_group(self, iommu_group):
            pci_table_by_iommu_group = self.get_pci_table_by_iommu_group()
            if iommu_group in pci_table_by_iommu_group:
                return pci_table_by_iommu_group[iommu_group]
            return Pci.PciList()

        def get_vga_list(self, mode=PciPassthroughMode.DEFAULT, vga_audio_passthrough_mode=PciPassthroughMode.NONE):
            result = Pci.PciList()
            for pci in self:
                if pci.class_code.is_vga():
                    result.add(pci)

            vga_audio_list = self.get_vga_audio_list(result, mode=vga_audio_passthrough_mode)
            result = self.get_passedthrough(result, mode=mode)
            result.update(vga_audio_list)
            return result

        def get_vga_audio_list(self, pci_vga_list, mode=PciPassthroughMode.DEFAULT):
            result = Pci.PciList()
            for pci in pci_vga_list:
                result.update(self.get_audio_list(subsystem_id=pci.subsystem_id, mode=mode))
            return result

        def get_audio_list(self, subsystem_id=None, mode=PciPassthroughMode.DEFAULT):
            result = Pci.PciList()
            for pci in self:
                if pci.class_code.is_audio():
                    if not subsystem_id:
                        result.add(pci)
                    elif subsystem_id == pci.subsystem_id:
                        result.add(pci)
            return self.get_passedthrough(result, mode=mode)

        def get_usb_host_list(self, mode=PciPassthroughMode.DEFAULT):
            result = Pci.PciList()
            for pci in self:
                if pci.class_code.is_usb_host_controller(pci.prog_if):
                    result.add(pci)
            return self.get_passedthrough(result, mode=mode)

        def get_isa_bridge_list(self, mode=PciPassthroughMode.DEFAULT):
            result = Pci.PciList()
            for pci in self:
                if pci.class_code.is_isa_bridge():
                    result.add(pci)
            return self.get_passedthrough(result, mode=mode)

        def get_pci_list_by_capabilities(self, is_pci_express=None, is_acs=None, is_sriov=None):
            result = Pci.PciList()
            for pci in self:
                if pci.is_capabilities(is_pci_express=is_pci_express, is_acs=is_acs, is_sriov=is_sriov):
                    result.add(pci)
            return result

        def is_each_device_in_its_own_iommu_group(self, pci_list_for_checking):
            pci_table_by_iommu_group = self.get_pci_table_by_iommu_group()

            for iommu_group, pci_list in pci_list_for_checking.get_pci_table_by_iommu_group().items():
                if iommu_group in pci_table_by_iommu_group:
                    if len(pci_table_by_iommu_group[iommu_group]) != len(pci_list):
                        return False
            return True

        ## Проверить IOMMU группы пробрасываемых PCI устройств: 1) в IOMMU группе нет не пробрасывамых устройств, 2) если правило (1) нарушается то поможет ли ACS override patch
        # @details Сравнение производится относительно self
        # @param [in] pci_list_for_checking Список PCI устройств для проверки
        # @return True - pci_list_for_checking можно пробросить без ограничений, False - pci_list_for_checking можно пробросить применив ACS override patch, None - pci_list_for_checking пробросить нельзя (в лог пишется информация о проблемных устройствах)
        def check_iommu_group_for_passthrough(self, pci_list_for_checking):
            pci_table_by_iommu_group = self.get_pci_table_by_iommu_group()
            result = True
            for iommu_group, pci_list in pci_list_for_checking.get_pci_table_by_iommu_group().items():
                if iommu_group in pci_table_by_iommu_group:
                    pci_list_by_iommu_group = pci_table_by_iommu_group[iommu_group]
                    if len(pci_list_by_iommu_group) != len(pci_list):
                        if len(pci_list.get_pci_list_by_capabilities(is_pci_express=True, is_acs=False)) != len(
                                pci_list):
                            # Условия для применения ACS override patch: PCI Express устройство (is_pci_express=True) и отсутствие capability ACS (is_acs=False)
                            # https://github.com/benbaker76/linux-acs-override/blob/main/6.3/acso.patch#L101
                            result = None
                            Logger.instance().warning(
                                f"[-] IOMMU group {iommu_group} will NOT be passedthrough completely:\n{pci_list_by_iommu_group.get_short_description(indent_spaces_count=4, pci_list_other=pci_list)}\n")
                        else:
                            if result is not None:
                                result = False
                            Logger.instance().info(
                                f"[o] IOMMU group {iommu_group} will be passedthrough completely if ASC override applicable:\n{pci_list_by_iommu_group.get_short_description(indent_spaces_count=4, pci_list_other=pci_list)}\n")
                    else:
                        Logger.instance().info(
                            f"[+] IOMMU group {iommu_group} will be passedthrough completely:\n{pci_list_by_iommu_group.get_short_description(indent_spaces_count=4, pci_list_other=pci_list_by_iommu_group)}\n")
            return result

        def get_passedthrough(self, target_pci_list, mode=PciPassthroughMode.DEFAULT):
            mode = PciPassthroughMode(mode)
            if mode.is_none():
                return []

            if mode.is_default():
                return target_pci_list

            result = []
            pci_table_by_iommu_group = self.get_pci_table_by_iommu_group()
            for iommu_group, pci_list in target_pci_list.get_pci_table_by_iommu_group().items():
                if iommu_group in pci_table_by_iommu_group:
                    if mode.is_flex():
                        if len(pci_table_by_iommu_group[iommu_group]) == len(pci_list):
                            result.extend(pci_table_by_iommu_group[iommu_group])
                    elif mode.is_force():
                        result.extend(pci_table_by_iommu_group[iommu_group])
            return result

        def get_by_address(self, pci_address_list: list[PciAddress]):
            result = Pci.PciList()
            for pci in self:
                if pci.address in pci_address_list:
                    result.add(pci)
            return result

        def get_pci_id_list(self) -> list[PciVidPid]:
            return [pci.get_id() for pci in self]

        ## Заблокировать ли прочие VGA для данной виртуальной машины
        # @details Требуется для обеспечения проброса Intel integrated GPU (IGD, Integrated Graphics Device) в так называемом legacy режиме, подробно https://gitlab.com/qemu-project/qemu/-/blob/master/docs/igd-assign.txt?ref_type=heads
        # @return true - заблокировать прочие VGA для данной виртуальной машины; false - можно использовать множественные VGA, в том числе виртуальные VGA
        def is_other_vga_disable(self) -> bool:
            for pci in self:
                if pci.is_other_vga_disable():
                    return True
            return False

        ## Проверить пригодность платформы (чипсета) для данной виртуальной машины
        # @details Некоторые сочетания Host BIOS/UEFI / Guest BIOS/UEFI не совместимы с пробросом PCI устройств
        # @details Если платформа (чипсет) не подходят метод бросит исключение с описанием проблемы
        # @param [in] qemu_platform Платформа (чипсет) виртуальной машины
        def check_platform(self, qemu_platform) -> None:
            for pci in self:
                pci.check_platform(qemu_platform)

        def to_sorted_list(self):
            result = list(self)
            result.sort(key=lambda x: x.address)
            return result

    @staticmethod
    def get_list(lspci_output_mock=None):
        result = Pci.PciList()

        lspci_out = lspci_output_mock if lspci_output_mock else Pci.__run_lspci()

        pci = None
        for match in re.finditer(Pci.__get_regex(), lspci_out, flags=re.MULTILINE):
            for key, value in match.groupdict().items():
                if value is not None:
                    if key == Pci.__ADDRESS:
                        if pci:
                            result.add(Pci.__build(pci))
                        pci = Pci()
                    pci[key] = value
        return result

    @staticmethod
    def __get_regex():
        tmp = Pci()
        result = ""
        result += fr"{tmp.get_regex_for(Pci.__ADDRESS)} "
        result += fr"{tmp.get_regex_for(Pci.__CLASS_NAME)} "
        result += fr"\[{tmp.get_regex_for(Pci.__CLASS_CODE)}\]: "
        result += fr"{tmp.get_regex_for(Pci.__DEVICE_NAME)} "
        result += fr"\[{tmp.get_regex_for(Pci.__DEVICE_ID)}\]"
        result += fr"(?> \(rev {tmp.get_regex_for(Pci.__REVISION)}\))?"
        result += fr"(?> \(prog-if {tmp.get_regex_for(Pci.__PROG_IF)} \[.*\]\))?"
        result += "|"
        result += fr"Subsystem: {tmp.get_regex_for(Pci.__SUBSYSTEM_NAME)} "
        result += fr"\[{tmp.get_regex_for(Pci.__SUBSYSTEM_ID)}\]"
        result += "|"
        result += fr"IOMMU group: {tmp.get_regex_for(Pci.__IOMMU_GROUP)}"
        result += "|"
        result += fr"Kernel driver in use: {tmp.get_regex_for(Pci.__KERNEL_MODULE)}"
        result += "|"
        result += fr"{tmp.get_regex_for(Pci.__IS_PCI_EXPRESS)}"
        result += "|"
        result += fr"{tmp.get_regex_for(Pci.__IS_ACS)}"
        result += "|"
        result += fr"{tmp.get_regex_for(Pci.__IS_SRIOV)}"
        return result

    @staticmethod
    def __build(base_pci):
        for sub_cls in get_all_subclasses(Pci):
            if sub_cls.is_my_instance(base_pci):
                return sub_cls(base_pci)
        return base_pci

    @staticmethod
    def __run_lspci() -> str:
        cmd_result = subprocess.run(Pci.__CMD_LINE, shell=True, capture_output=True, text=True)
        if cmd_result.returncode:
            return ""
        return cmd_result.stdout
