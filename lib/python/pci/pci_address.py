import re

from lib.python.utils import BaseParser, UInt8, UInt8Hex, UInt16Hex


class PciAddress(BaseParser):
    __DOMAIN = "domain"
    __BUS = "bus"
    __SLOT = "slot"
    __FUNC = "func"

    DOMAIN_DEFAULT = "0000"

    __TABLE = {__DOMAIN: {"type": UInt16Hex, "default": DOMAIN_DEFAULT},
               __BUS: {"type": UInt8Hex},
               __SLOT: {"type": UInt8Hex},
               __FUNC: {"type": UInt8}}

    def __init__(self, pci_address=None):
        super(PciAddress, self).__init__(PciAddress.__TABLE)
        if pci_address is None:  # Создать умолчательный объект
            return

        if self.copy_if(pci_address):  # Копирующий конструктор (в том числе если pci_address - это словарь)
            return

        # Создать объект из строки, например, из результата разбора выхлопа lspci
        if self.init_fields(re.compile(PciAddress.get_regex(is_capture=True, is_start_end_of_line=False)),
                            pci_address):
            return

        raise Exception(f"[PciAddress] Format FAIL: {pci_address} | {type(pci_address)}")

    def __str__(self):
        return f"{self.domain}:{self.get_address_without_domain()}"

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        if other is self:
            return True
        return self.__str__() == other.__str__()

    def __lt__(self, other):
        if not isinstance(other, PciAddress):
            other = PciAddress(other)
        if self.domain < other.domain:
            return True
        elif self.domain > other.domain:
            return False
        elif self.bus < other.bus:
            return True
        elif self.bus > other.bus:
            return False
        elif self.slot < other.slot:
            return True
        elif self.slot > other.slot:
            return False
        elif self.func < other.func:
            return True
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __le__(self, other):
        return self.__lt__(other) or self.__eq__(other)

    def __gt__(self, other):
        return not self.__le__(other)

    def __ge__(self, other):
        return not self.__lt__(other)

    def get_address_without_domain(self):
        return f"{self.bus}:{self.slot}.{self.func}"

    @staticmethod
    def get_regex(is_capture=False, is_start_end_of_line=False):
        tmp = PciAddress()
        result = ""
        if is_start_end_of_line:
            result += "^"
        result += fr"(?>{tmp.get_regex_for(PciAddress.__DOMAIN, is_capture)}:)?"
        result += fr"{tmp.get_regex_for(PciAddress.__BUS, is_capture)}:"
        result += fr"{tmp.get_regex_for(PciAddress.__SLOT, is_capture)}\."
        result += fr"{tmp.get_regex_for(PciAddress.__FUNC, is_capture)}"
        if is_start_end_of_line:
            result += "$"
        return result
