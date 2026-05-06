import re

from lib.python.utils import BaseParser, UInt16Hex


# https://github.com/pciutils/pciutils/blob/master/pci.ids
class PciVidPid(BaseParser):
    INTEL = 0x8086

    __VID = "vid"
    __PID = "pid"

    __SEPARATOR = ":"

    __TABLE = {__VID: {"type": UInt16Hex},
               __PID: {"type": UInt16Hex}}

    def __init__(self, vid_pid=None):
        super(PciVidPid, self).__init__(PciVidPid.__TABLE)
        if vid_pid is None:  # Создать умолчательный объект
            return

        if self.copy_if(vid_pid):  # Копирующий конструктор (в том числе если vid_pid - это словарь)
            return

        # Создать объект из строки, например, из результата разбора выхлопа lspci
        if self.init_fields(re.compile(PciVidPid.get_regex(is_capture=True, is_start_end_of_line=False)),
                            vid_pid):
            return

        raise Exception(f"[PciAddress] Format FAIL: {vid_pid} | {type(vid_pid)}")

    def __str__(self):
        return f"{self.vid}{self.__SEPARATOR}{self.pid}"

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        if other is self:
            return True
        return self.__str__() == other.__str__()

    def __lt__(self, other):
        if not isinstance(other, PciAddress):
            other = PciAddress(other)
        if self.vid < other.vid:
            return True
        elif self.vid > other.vid:
            return False
        elif self.pid < other.pid:
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

    @staticmethod
    def get_regex(is_capture=False, is_start_end_of_line=False):
        tmp = PciVidPid()
        result = ""
        if is_start_end_of_line:
            result += "^"
        result += fr"{tmp.get_regex_for(PciVidPid.__VID, is_capture)}{PciVidPid.__SEPARATOR}"
        result += fr"{tmp.get_regex_for(PciVidPid.__PID, is_capture)}"
        if is_start_end_of_line:
            result += "$"
        return result

    def is_intel(self):
        return self.vid == self.INTEL
