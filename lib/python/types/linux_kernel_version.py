import re

from base_parser import BaseParser
from string_types import StringAsciiPrintable


class LinuxKernelVersion(BaseParser):
    class Number(int):
        @staticmethod
        def get_regex() -> str:
            return "[0-9]{1,4}"

    __MAJOR = "major"
    __MINOR = "minor"
    __REVISION = "revision"
    __RELEASE_CANDIDATE = "release_candidate"
    __PATCH = "patch"
    __VARIANT = "variant"

    __TABLE = {__MAJOR: {"type": Number, "default": 0},
               __MINOR: {"type": Number, "default": 0},
               __REVISION: {"type": Number, "default": 0},
               __RELEASE_CANDIDATE: {"type": Number, "default": 0},
               __PATCH: {"type": Number, "default": 0},
               __VARIANT: {"type": StringAsciiPrintable, "default": ""}
               }

    def __init__(self, linux_kernel_version=None):
        super(LinuxKernelVersion, self).__init__(LinuxKernelVersion.__TABLE)
        if linux_kernel_version is None:  # Создать умолчательный объект
            return

        if self.copy_if(linux_kernel_version):  # Копирующий конструктор (в том числе если pci_address - это словарь)
            return

        # Создать объект из строки, например, из результата разбора выхлопа lspci
        if self.init_fields(re.compile(LinuxKernelVersion.get_regex()),
                            linux_kernel_version):
            return

        raise Exception(f"[LinuxKernelVersion] Format FAIL: {linux_kernel_version} | {type(linux_kernel_version)}")

    def __str__(self):
        result = f"{self.major}.{self.minor}"
        if self.revision > 0:
            result += f".{self.revision}"

        if self.release_candidate > 0:
            result += f"-rc{self.release_candidate}"

        if self.patch > 0:
            result += f"-{self.patch}"

        if len(self.variant) > 0:
            result += f"-{self.variant}"

        return result

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        if not isinstance(other, LinuxKernelVersion):
            other = LinuxKernelVersion(other)
        return self.major == other.major and self.minor == other.minor and self.revision == other.revision and self.release_candidate == other.release_candidate and self.patch == other.patch and self.variant == other.variant

    def __lt__(self, other):
        if not isinstance(other, LinuxKernelVersion):
            other = LinuxKernelVersion(other)
        if self.major < other.major:
            return True
        elif self.major > other.major:
            return False
        elif self.minor < other.minor:
            return True
        elif self.minor > other.minor:
            return False
        elif self.revision < other.revision:
            return True
        elif self.revision > other.revision:
            return False
        elif self.release_candidate < other.release_candidate:
            return True
        elif self.release_candidate > other.release_candidate:
            return False
        elif self.patch < other.patch:
            return True
        elif self.patch > other.patch:
            return False
        elif self.variant < other.variant:
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

    def is_rc(self):
        return self.release_candidate > 0

    def is_liquorix(self):
        return "liquorix" in self.variant.lower()

    @staticmethod
    def get_regex():
        is_capture = True
        tmp = LinuxKernelVersion()
        result = ""
        result += fr"{tmp.get_regex_for(LinuxKernelVersion.__MAJOR, is_capture)}\."
        result += fr"{tmp.get_regex_for(LinuxKernelVersion.__MINOR, is_capture)}"
        result += fr"(?>\.{tmp.get_regex_for(LinuxKernelVersion.__REVISION, is_capture)})?"
        result += fr"(?>-rc{tmp.get_regex_for(LinuxKernelVersion.__RELEASE_CANDIDATE, is_capture)})?"
        result += fr"(?>-{tmp.get_regex_for(LinuxKernelVersion.__PATCH, is_capture)})?"
        result += fr"(?>[\.-]{tmp.get_regex_for(LinuxKernelVersion.__VARIANT, is_capture)})?"
        result += "$"
        return result