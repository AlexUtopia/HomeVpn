import argparse
import asyncio
import copy
import hashlib
import shutil
import atexit
import os.path
import stat
import re
import shlex
import subprocess
import json
import ipaddress
import tempfile
import threading
import time
import sys
import urllib.request
import urllib.parse
import uuid

import netaddr
import os_release
import randmac
import unittest
from crontab import CronTab
import datetime
import pathlib
import getpass

import requests

# fixme utopia Исправление для iptc который неадекватно работает на Ubuntu 22.04
import semantic_version

# Настройка firewall для вирт машин
# http://rhd.ru/docs/manuals/enterprise/RHEL-4-Manual/security-guide/s1-firewall-ipt-fwd.html

os.environ['XTABLES_LIBDIR'] = "/usr/lib/x86_64-linux-gnu/xtables/"

import psutil
import stun
import iptc  # fixme utopia Перейти на nftables, iptables оставить под конфигом проекта
# https://habr.com/ru/companies/ruvds/articles/580648/
import socket
import platform
import cpuinfo
import logging
import logging.handlers


class Logger:
    class LoggerImpl:
        __LOG_NAME = "HomeVpn"

        def __init__(self):
            self.__logger = logging.getLogger(self.__LOG_NAME)
            self.__logger.setLevel(logging.DEBUG)
            file_handler = logging.handlers.TimedRotatingFileHandler(self.__get_log_file_path(),
                                                                     when='midnight', encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(
                logging.Formatter(
                    fmt='{asctime} {levelname: <8} {message} [{process}][{thread}] <{funcName}:{lineno}>',
                    style='{'))
            self.__logger.addHandler(file_handler)

            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(logging.Formatter(fmt='{asctime} {levelname: <8} {message}', style='{'))
            self.__logger.addHandler(console_handler)

        def get_logger(self):
            return self.__logger

        def __get_log_file_path(self):
            return self.__get_logging_dir_path() / f"{datetime.datetime.now():%Y-%m-%d}_{self.__LOG_NAME}.log"

        def __get_logging_dir_path(self):
            result = self.__get_current_dir_path() / "logs"
            result.mkdir(parents=True, exist_ok=True)
            return result

        def __get_current_dir_path(self):
            return pathlib.Path(__file__).resolve().parent

    __instance = LoggerImpl()

    @staticmethod
    def instance():
        return Logger.__instance.get_logger()


class RegexConstants:
    CAPTURE_ALL = fr"(.*)"
    WHITESPACES = r"\s"
    WHITESPACE_CHARACTER_SET = fr"[{WHITESPACES}]"
    SPACE_SYMBOLS_ZERO_OR_MORE = fr"{WHITESPACE_CHARACTER_SET}*"
    SPACE_SYMBOLS_ONE_OR_MORE = fr"{WHITESPACE_CHARACTER_SET}+"
    NEWLINE_CHARACTER_SET = r"[\n\r]"
    ONE_OR_MORE_NEW_LINES = fr"{NEWLINE_CHARACTER_SET}+"
    ZERO_OR_MORE_NEW_LINES = fr"{NEWLINE_CHARACTER_SET}*"
    ONE_OR_MORE_WHITESPACES = fr"{WHITESPACE_CHARACTER_SET}+"
    ZERO_OR_MORE_WHITESPACES = fr"{WHITESPACE_CHARACTER_SET}*"
    ASCII_LETTER = "a-zA-Z"
    ASCII_LETTER_CHARACTER_SET = f"[{ASCII_LETTER}]"
    ASCII_PRINTABLE = "\\x20-\\x7E"
    ASCII_PRINTABLE_CHARACTER_SET = f"[{ASCII_PRINTABLE}]"

    ENCODE_TABLE_FOR_CHARACTER_SET = [("\\", "\\\\"), (".", "\."), ("[", "\["), ("]", "\]"), ("(", "\("),
                                      (")", "\)"), ("$", "\$"), ("-", "\-"), (">", "\>"),
                                      ("<", "\<"), ("|", "\|"), ("?", "\?"), ("^", "\^")]

    @staticmethod
    def atomic_group(value):
        return f"(?>{value})"

    @staticmethod
    def to_character_set(character_set, is_remove_duplicate=True):
        result = ""
        if isinstance(character_set, list) or isinstance(character_set, set):
            for item in character_set:
                result += RegexConstants.to_character_set(item)
            result = RegexConstants.to_character_set(result)
        elif isinstance(character_set, str):
            if is_remove_duplicate:
                character_set_as_list = list(set(character_set))
                character_set_as_list.sort()
                result = "".join(character_set_as_list)
            else:
                result = character_set
        return result

    @staticmethod
    def character_set_escape(character_set, is_remove_duplicate=True):
        return EscapeLiteral(encode_table=RegexConstants.ENCODE_TABLE_FOR_CHARACTER_SET).encode(
            RegexConstants.to_character_set(character_set, is_remove_duplicate))


class BitUtils:
    DECIMAL_BASE = 10
    HEXADECIMAL_BASE = 16
    OCTAL_BASE = 8
    BINARY_BASE = 2
    TETRAD_IN_BYTE = 2
    BITS_IN_TETRAD = 4
    LSB_TETRAD_MASK = 0x0F
    MSB_TETRAD_MASK = 0xF0
    BITS_IN_BYTE = BITS_IN_TETRAD * TETRAD_IN_BYTE
    UINT8_MIN = 0
    UINT8_MAX = 0xFF
    INT8_MIN = -128
    INT8_MAX = 127
    UINT16_MIN = 0
    UINT16_MAX = 0xFFFF
    INT16_MIN = -32768
    INT16_MAX = 32767
    UINT8_MASK = UINT8_MAX
    UINT16_MASK = UINT16_MAX
    BIT_COUNT_MAX = sys.maxsize.bit_length() + 1
    BASE_DIGIT_LIST = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    BASE_MIN = 2
    BASE_MAX = len(BASE_DIGIT_LIST)
    DIGIT_COUNT_MIN = 1

    @staticmethod
    def is_decimal(val_as_string):
        regex = re.compile(BitUtils.__get_regex_for_check_int(base=BitUtils.DECIMAL_BASE, prefix="(?!0[0-9])"),
                           re.MULTILINE | re.IGNORECASE)
        match = regex.search(val_as_string)
        return match is not None

    @staticmethod
    def is_hexadecimal(val_as_string):
        regex = re.compile(BitUtils.__get_regex_for_check_int(base=BitUtils.HEXADECIMAL_BASE, prefix="0x[0]*"),
                           re.MULTILINE | re.IGNORECASE)
        match = regex.search(val_as_string)
        return match is not None

    @staticmethod
    def is_binary(val_as_string):
        regex = re.compile(BitUtils.__get_regex_for_check_int(base=BitUtils.BINARY_BASE, prefix="0b[0]*"),
                           re.MULTILINE | re.IGNORECASE)
        match = regex.search(val_as_string)
        return match is not None

    @staticmethod
    def is_octal(val_as_string):
        regex = re.compile(BitUtils.__get_regex_for_check_int(base=BitUtils.OCTAL_BASE, prefix="0[0]*"),
                           re.MULTILINE | re.IGNORECASE)
        match = regex.search(val_as_string)
        return match is not None

    @staticmethod
    def __get_regex_for_check_int(base, prefix):
        BitUtils.__check_base(base)
        return f"^(?>\+|-|){prefix}[{BitUtils.BASE_DIGIT_LIST[0]}-{BitUtils.BASE_DIGIT_LIST[base - 1]}]{{1,{BitUtils.get_digit_count_max(base)}}}$"

    @staticmethod
    def get_int_with_check(val, bit_count=BIT_COUNT_MAX, signed=True, base=DECIMAL_BASE):
        BitUtils.__check_base(base)
        result = 0
        if isinstance(val, str):
            result = int(val, base)
        elif isinstance(val, int):
            result = val
        else:
            raise Exception(f"Value unknown type: {val} | {type(val)}")
        BitUtils.check_int(result, bit_count, signed)
        return result

    @staticmethod
    def get_regex(val_max, base):
        BitUtils.__check_int_type(val_max)
        val_max = abs(val_max)

        val_max_as_str = BitUtils.to_string(val_max, base)
        digit_count = len(val_max_as_str)

        # Заполнение всех digits нулями, пробелами или ничем

        # Правило для первого элемента, последнего элемента, и всех прочих

        # регулярка для val_max = 157, заполнение нулями
        # [0-1](?(?<=1)[0-5]|[0-9])(?(?<=15)[0-6]|[0-9])
        # [1-10](?(?<=1)[0-5]|(?(?<=0)[1-90]|[0-5]))(?(?<=15)[0-6]|[0-9])

        # регулярка для val_max = 157, заполнение пробелами
        # [1-1 ](?(?<=1)[0-5]|(?(?<= )[1-9 ]|[0-5]))(?(?<=15)[0-6]|[0-9])

        # регулярка для val_max = 157, заполнение ничем
        # ограничение по максимальной разрядности
        # [1-1]{0,1}+(?(?<=1)[0-5]|[0-9]){0,1}+(?(?<=15)[0-6]|[0-9])
        # добавляется ревнивая квантификация и оптимизация условия 2.1

        # диапазон 0 до val_max
        #

        # Система счисления запись
        return ""

    @staticmethod
    def check_int(val, bit_count, signed):
        BitUtils.__check_int_type(val)
        val_min = BitUtils.get_int_min_value(bit_count, signed)
        val_max = BitUtils.get_int_max_value(bit_count, signed)
        BitUtils.__check_range(val, val_min, val_max)

    @staticmethod
    def to_string(val, base, to_lower=False):
        BitUtils.__check_int_type(val)
        BitUtils.__check_base(base)
        if val == 0:
            return "0"

        result = ""
        if val < 0:
            result += "-"
            val = abs(val)

        while val > 0:
            result += BitUtils.BASE_DIGIT_LIST[val % base]
            val = val / base
        result = result[::-1]
        if to_lower:
            return result.lower()
        return result

    @staticmethod
    def get_max_by_base(base, digit_count):
        BitUtils.__check_base(base)
        # BitUtils.__check_digit_count(digit_count) # fixme utopia Сделать

        digit_value_max = BitUtils.get_digit_value_max(base)
        result = 0
        while digit_count > 0:
            result = (result * base) + digit_value_max
            digit_count = digit_count - 1
        return result

    @staticmethod
    def get_digit_value_max(base):
        BitUtils.__check_base(base)
        return base - 1

    @staticmethod
    def get_digit_count_max(base, bit_count=BIT_COUNT_MAX):
        BitUtils.__check_base(base)
        int_max = BitUtils.get_int_max_value(bit_count, signed=False)
        # Теоретически может быть -1 (int64 = 0xFFFFFFFFFFFFFFFF), например, для Python2
        return BitUtils.get_digit_count(int_max, base)

    @staticmethod
    def get_digit_count(val, base):
        BitUtils.__check_int_type(val)
        BitUtils.__check_base(base)
        if val == 0:
            return 1
        val = abs(val)

        result = 0
        while val > 0:
            val = val // base
            result = result + 1
        return result

    @staticmethod
    def get_min_by_base(base, digit_count):
        return 0

    @staticmethod
    def get_int_min_max_value(bit_count, signed):
        return BitUtils.get_int_min_value(bit_count, signed), BitUtils.get_int_max_value(bit_count, signed)

    @staticmethod
    def get_int_min_value(bit_count, signed):
        BitUtils.__check_bit_count(bit_count)
        if signed:
            return ~0 << bit_count - 1
        return 0

    @staticmethod
    def get_int_max_value(bit_count, signed):
        BitUtils.__check_bit_count(bit_count)
        if signed:
            return ~(~0 << bit_count - 1)
        return ~(~0 << bit_count)

    @staticmethod
    def __check_bit_count(bit_count):
        BitUtils.__check_int_type(bit_count)
        bit_count_min = 1
        bit_count_max = BitUtils.BIT_COUNT_MAX
        BitUtils.__check_range(bit_count, bit_count_min, bit_count_max)

    @staticmethod
    def __check_base(base):
        BitUtils.__check_int_type(base)
        BitUtils.__check_range(base, BitUtils.BASE_MIN, BitUtils.BASE_MAX)

    @staticmethod
    def __check_int_type(val):
        if not isinstance(val, int):
            raise Exception("Value unknown type, must be int: {}".format(str(val)))

    @staticmethod
    def __check_range(val, val_min, val_max):
        if val_min > val_max:
            raise Exception("Value min ({}) more value max ({}))".format(val_min, val_max))
        if val_min > val > val_max:
            raise Exception("Value invalid range: {}, (min={}, max={})".format(str(val), val_min, val_max))


class UnitTest_BitUtils(unittest.TestCase):

    def test_is_decimal(self):
        ref_table = {
            "1": [(10, True), (16, False), (2, False), (8, False)],
            "-1": [(10, True), (16, False), (2, False), (8, False)],
            "0": [(10, True), (16, False), (2, False), (8, False)],
            "9999": [(10, True), (16, False), (2, False), (8, False)],
            "-9999": [(10, True), (16, False), (2, False), (8, False)],
            "+9999": [(10, True), (16, False), (2, False), (8, False)],
            "0x0": [(10, False), (16, True), (2, False), (8, False)],
            "0x00": [(10, False), (16, True), (2, False), (8, False)],
            "0x0000": [(10, False), (16, True), (2, False), (8, False)],
            "0x00000000": [(10, False), (16, True), (2, False), (8, False)],
            "0x0000000000000000": [(10, False), (16, True), (2, False), (8, False)],
            "0x00000000000000000000000000000000": [(10, False), (16, True), (2, False), (8, False)],
            "-0xff": [(10, False), (16, True), (2, False), (8, False)],
            "+0xFe": [(10, False), (16, True), (2, False), (8, False)],
            "+0x0000123456789ABCDEF": [(10, False), (16, True), (2, False), (8, False)],
            "-0xFFFFFFFFFFFFFFFF": [(10, False), (16, True), (2, False), (8, False)],
            "+0xFFFFFFFFFFFFFFFF": [(10, False), (16, True), (2, False), (8, False)],
            "0b0": [(10, False), (16, False), (2, True), (8, False)],
            "0b00000000": [(10, False), (16, False), (2, True), (8, False)],
            "-0b010101010101": [(10, False), (16, False), (2, True), (8, False)],
            "+0b010101010101": [(10, False), (16, False), (2, True), (8, False)],
            "01": [(10, False), (16, False), (2, False), (8, True)],
            "-01": [(10, False), (16, False), (2, False), (8, True)],
            "+01": [(10, False), (16, False), (2, False), (8, True)],
            "07": [(10, False), (16, False), (2, False), (8, True)],
            "00": [(10, False), (16, False), (2, False), (8, True)],
            "01234567890ABCDEF": [(10, False), (16, False), (2, False), (8, False)]
        }

        for key, table in ref_table.items():
            for base, result in table:
                if base == 10:
                    self.assertEqual(BitUtils.is_decimal(key), result, f"base={base}, key={key}")
                elif base == 16:
                    self.assertEqual(BitUtils.is_hexadecimal(key), result, f"base={base}, key={key}")
                elif base == 2:
                    self.assertEqual(BitUtils.is_binary(key), result, f"base={base}, key={key}")
                elif base == 8:
                    self.assertEqual(BitUtils.is_octal(key), result, f"base={base}, key={key}")
                else:
                    self.assertTrue(False, f"Unknown base={base}")

    def test_get_digit_count(self):
        ref_table = {
            "9999": (10, 4),
            "10": (10, 2),
            "0xFFFF": (16, 4),
            "0x00FFFF": (16, 4),
            "0xFFFFFFFF": (16, 8),
            "0xFFFFFFFFFFFFFFFF": (16, 16),
            "0b0101": (2, 3),
            "012": (8, 2)
        }

        for key, value in ref_table.items():
            base, result = value
            self.assertEqual(BitUtils.get_digit_count(int(key, base), base), result, f"base={base}, key={key}")


class UInt8Hex(int):
    def __new__(cls, value=0):
        return super(UInt8Hex, cls).__new__(cls, BitUtils.get_int_with_check(value, bit_count=8, signed=False,
                                                                             base=BitUtils.HEXADECIMAL_BASE))

    def __str__(self):
        return f"{int(self):02x}"

    @staticmethod
    def get_regex():
        return "[0-9a-fA-F]{2}"


class UInt16Hex(int):
    def __new__(cls, value=0):
        return super(UInt16Hex, cls).__new__(cls, BitUtils.get_int_with_check(value, bit_count=16, signed=False,
                                                                              base=BitUtils.HEXADECIMAL_BASE))

    def __str__(self):
        return f"{int(self):04x}"

    @staticmethod
    def get_regex():
        return "[0-9a-fA-F]{4}"


class UInt8(int):
    def __new__(cls, value=0):
        return super(UInt8, cls).__new__(cls, BitUtils.get_int_with_check(value, bit_count=8, signed=False,
                                                                          base=BitUtils.DECIMAL_BASE))

    def __str__(self):
        return f"{int(self)}"

    @staticmethod
    def get_regex():
        return f"[0-9]{{1,{BitUtils.get_digit_count_max(BitUtils.DECIMAL_BASE, bit_count=8)}}}"


class String(str):

    @staticmethod
    def get_regex():
        return f".+"


class StringAsciiLetter(str):

    @staticmethod
    def get_regex():
        return f"{RegexConstants.ASCII_LETTER_CHARACTER_SET}+"


class StringAsciiPrintable(str):

    @staticmethod
    def get_regex():
        return f"{RegexConstants.ASCII_PRINTABLE_CHARACTER_SET}+"


class StringAsciiWords(str):

    @staticmethod
    def get_regex():
        return f"[\w \-,.]+"


class BaseParser:
    def __init__(self, table):
        self.__table = table
        self.init_fields_default()

    def __setitem__(self, key, value):
        metadata = self.__table.get(key)
        if metadata is None:
            return

        field_type = self.__get_field_type(metadata)
        if field_type is None:
            return

        if value is None:
            setattr(self, key, value)
            return

        setattr(self, key, field_type(value))

    def __getitem__(self, key):
        return getattr(self, key)

    def __str__(self):
        return json.dumps(self.get_fields_as_dict())

    def __repr__(self):
        return self.__str__()

    def get_fields_as_dict(self):
        result = dict()
        for field_name, metadata in self.__table.items():
            field_value = self[field_name]
            if isinstance(field_value, BaseParser):
                result[field_name] = field_value.get_fields_as_dict()
            else:
                result[field_name] = field_value
        return result

    def init_fields_default(self):
        for field_name, metadata in self.__table.items():
            if "default" in metadata:
                self[field_name] = metadata.get("default")
            else:
                setattr(self, field_name, self.__get_field_type(metadata)())

    def init_fields(self, re_object, value_as_str):
        if not isinstance(value_as_str, str):
            return False

        match = re_object.search(str(value_as_str))
        if match is None:
            return False

        for field_name, value in match.groupdict().items():
            if value is not None:
                self[field_name] = value
        return True

    def copy_if(self, other):
        if isinstance(other, type(self)) or isinstance(self, type(other)) or isinstance(other, dict):
            other_dict = other if isinstance(other, dict) else other.get_fields_as_dict()
            for field_name, metadata in self.__table.items():
                if field_name in other_dict:
                    self[field_name] = other[field_name]
                else:
                    setattr(self, field_name, self.__get_field_type(metadata)())
            return True
        else:
            return False

    # @staticmethod
    # def from_string(model):
    #     Pci.from_json(json.loads(model))
    #
    # @staticmethod
    # def from_json(model):
    #     result = Pci()
    #     for key, value in model.items():
    #         result[key] = value
    #     return Pci.__build(result)

    def get_regex_for(self, field_name, is_capture=True):
        metadata = self.__table.get(field_name)
        if metadata is None:
            return ""

        field_type = self.__get_field_type(metadata)
        if field_type is None:
            return ""

        if is_capture:
            return f"(?P<{field_name}>{field_type.get_regex()})"
        else:
            return field_type.get_regex()

    def __get_field_type(self, metadata):
        return metadata.get("type")


class LinuxKernelVersion(BaseParser):
    class Number(int):
        @staticmethod
        def get_regex():
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
               __VARIANT: {"type": String, "default": ""}
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
        result += f"{tmp.get_regex_for(LinuxKernelVersion.__MAJOR, is_capture)}\."
        result += f"{tmp.get_regex_for(LinuxKernelVersion.__MINOR, is_capture)}"
        result += f"(?>\.{tmp.get_regex_for(LinuxKernelVersion.__REVISION, is_capture)})?"
        result += f"(?>-rc{tmp.get_regex_for(LinuxKernelVersion.__RELEASE_CANDIDATE, is_capture)})?"
        result += f"(?>-{tmp.get_regex_for(LinuxKernelVersion.__PATCH, is_capture)})?"
        result += f"(?>[\.-]{tmp.get_regex_for(LinuxKernelVersion.__VARIANT, is_capture)})?"
        result += f"$"
        return result


class UnitTest_LinuxKernelVersion(unittest.TestCase):
    class LinuxKernelVersionTest(LinuxKernelVersion):
        pass

    class UnknownClass:
        pass

    def test(self):
        ref_table = [
            (LinuxKernelVersion, "",
             {"is_exception": True}),
            (LinuxKernelVersion, "Hello world",
             {"is_exception": True}),
            (LinuxKernelVersion, 17,
             {"is_exception": True}),
            (LinuxKernelVersion, UnitTest_LinuxKernelVersion.UnknownClass,
             {"is_exception": True}),
            (LinuxKernelVersion, "5",
             {"is_exception": True}),
            (LinuxKernelVersion, "5.",
             {"is_exception": True}),
            (LinuxKernelVersion, "5.0-",
             {"is_exception": True}),
            (LinuxKernelVersion, "6.14.0-1-liquorix-amd64",
             {"expected": "6.14-1-liquorix-amd64", "is_exception": False, "is_liquorix": True, "is_rc": False,
              "expected_dict": {"major": 6, "minor": 14, "revision": 0, "release_candidate": 0, "patch": 1,
                                "variant": "liquorix-amd64"}}),
            (LinuxKernelVersion, "/boot/vmlinuz-5.15.0-91-generic",
             {"expected": "5.15-91-generic", "is_exception": False, "is_liquorix": False, "is_rc": False,
              "expected_dict": {"major": 5, "minor": 15, "revision": 0, "release_candidate": 0, "patch": 91,
                                "variant": "generic"}}),
            (LinuxKernelVersion, "6.14-rc15",
             {"expected": "6.14-rc15", "is_exception": False, "is_liquorix": False, "is_rc": True,
              "expected_dict": {"major": 6, "minor": 14, "revision": 0, "release_candidate": 15, "patch": 0,
                                "variant": ""}}),
            (LinuxKernelVersion, "6.14.9999-rc15",
             {"expected": "6.14.9999-rc15", "is_exception": False, "is_liquorix": False, "is_rc": True,
              "expected_dict": {"major": 6, "minor": 14, "revision": 9999, "release_candidate": 15, "patch": 0,
                                "variant": ""}}),
            (LinuxKernelVersion, "6.14.9999-rc15fff",
             {"expected": "6.14.9999-rc15fff", "is_exception": False, "is_liquorix": False, "is_rc": False,
              "expected_dict": {"major": 6, "minor": 14, "revision": 9999, "release_candidate": 0, "patch": 0,
                                "variant": "rc15fff"}}),
            (LinuxKernelVersion, "6.14-012345ggg",
             {"expected": "6.14-012345ggg", "is_exception": False, "is_liquorix": False, "is_rc": False,
              "expected_dict": {"major": 6, "minor": 14, "revision": 0, "release_candidate": 0, "patch": 0,
                                "variant": "012345ggg"}}),
            (LinuxKernelVersion, {"major": 1, "minor": 2},
             {"expected": f"1.2", "is_exception": False, "is_liquorix": False, "is_rc": False,
              "expected_dict": {"major": 1, "minor": 2, "revision": 0, "release_candidate": 0, "patch": 0,
                                "variant": ""}}),
            (LinuxKernelVersion, {"major1": 1, "minor": 2},
             {"expected": f"0.2", "is_exception": False, "is_liquorix": False, "is_rc": False,
              "expected_dict": {"major": 0, "minor": 2, "revision": 0, "release_candidate": 0, "patch": 0,
                                "variant": ""}}),
            (LinuxKernelVersion, None,
             {"expected": f"0.0", "is_exception": False, "is_liquorix": False, "is_rc": False,
              "expected_dict": {"major": 0, "minor": 0, "revision": 0, "release_candidate": 0, "patch": 0,
                                "variant": ""}}),
            (LinuxKernelVersion, {},
             {"expected": f"0.0", "is_exception": False, "is_liquorix": False, "is_rc": False,
              "expected_dict": {"major": 0, "minor": 0, "revision": 0, "release_candidate": 0, "patch": 0,
                                "variant": ""}}),
            (LinuxKernelVersion, LinuxKernelVersion(),
             {"expected": f"0.0", "is_exception": False, "is_liquorix": False, "is_rc": False,
              "expected_dict": {"major": 0, "minor": 0, "revision": 0, "release_candidate": 0, "patch": 0,
                                "variant": ""}}),
            (LinuxKernelVersion, LinuxKernelVersion("1.2"),
             {"expected": f"1.2", "is_exception": False, "is_liquorix": False, "is_rc": False,
              "expected_dict": {"major": 1, "minor": 2, "revision": 0, "release_candidate": 0, "patch": 0,
                                "variant": ""}}),
            (LinuxKernelVersion, UnitTest_LinuxKernelVersion.LinuxKernelVersionTest("1.2"),
             {"expected": f"1.2", "is_exception": False, "is_liquorix": False, "is_rc": False,
              "expected_dict": {"major": 1, "minor": 2, "revision": 0, "release_candidate": 0, "patch": 0,
                                "variant": ""}}),
            (UnitTest_LinuxKernelVersion.LinuxKernelVersionTest, LinuxKernelVersion("1.2"),
             {"expected": f"1.2", "is_exception": False, "is_liquorix": False, "is_rc": False,
              "expected_dict": {"major": 1, "minor": 2, "revision": 0, "release_candidate": 0, "patch": 0,
                                "variant": ""}})
        ]

        for class_type, initiate, test_data in ref_table:
            target = None
            try:
                target = class_type(initiate)
                self.assertFalse(test_data["is_exception"], f"No exception for \"{initiate}\"")
            except Exception as ex:
                self.assertTrue(test_data["is_exception"], f"Exception for \"{initiate}\": {ex}")

            if target is not None:
                self.assertEqual(target.get_fields_as_dict(), test_data["expected_dict"])
                self.assertEqual(str(class_type(initiate)), test_data["expected"])
                self.assertEqual(target.is_liquorix(), test_data["is_liquorix"])
                self.assertEqual(target.is_rc(), test_data["is_rc"])

    def test_compare(self):
        ref_table = [
            {"first": "6.12", "second": "6.12.0-0", "compare":
                {"==": True, "!=": False, ">": False, ">=": True, "<": False, "<=": True}},
            {"first": "6.15", "second": "6.12", "compare":
                {"==": False, "!=": True, ">": True, ">=": True, "<": False, "<=": False}},
            {"first": "6.15.1", "second": "6.15", "compare":
                {"==": False, "!=": True, ">": True, ">=": True, "<": False, "<=": False}},
            {"first": "6.15-rc1", "second": "6.15.1", "compare":
                {"==": False, "!=": True, ">": False, ">=": False, "<": True, "<=": True}},
            {"first": "6.15.1-rc1", "second": "6.15.1", "compare":
                {"==": False, "!=": True, ">": True, ">=": True, "<": False, "<=": False}},
            {"first": "6.15.1", "second": "6.15.1-1", "compare":
                {"==": False, "!=": True, ">": False, ">=": False, "<": True, "<=": True}},
            {"first": "6.15.1-generic", "second": "6.15.1-liquorix", "compare":
                {"==": False, "!=": True, ">": False, ">=": False, "<": True, "<=": True}},
            {"first": "5.15-133-generic", "second": "6.5-35-generic", "compare":
                {"==": False, "!=": True, ">": False, ">=": False, "<": True, "<=": True}}
        ]

        for item in ref_table:
            first = LinuxKernelVersion(item["first"])
            second = LinuxKernelVersion(item["second"])
            for operation, expected in item["compare"].items():
                if operation == "==":
                    self.assertEqual(first == second, expected, f"{first} {operation} {second}")
                elif operation == "!=":
                    self.assertEqual(first != second, expected, f"{first} {operation} {second}")
                elif operation == ">":
                    self.assertEqual(first > second, expected, f"{first} {operation} {second}")
                elif operation == ">=":
                    self.assertEqual(first >= second, expected, f"{first} {operation} {second}")
                elif operation == "<":
                    self.assertEqual(first < second, expected, f"{first} {operation} {second}")
                elif operation == "<=":
                    self.assertEqual(first <= second, expected, f"{first} {operation} {second}")

    def test_sort(self):
        test_data = [LinuxKernelVersion("6.14-1-liquorix-amd64"), LinuxKernelVersion("5.15-133-generic"),
                     LinuxKernelVersion("5.15-134-generic"), LinuxKernelVersion("5.15-136-generic"),
                     LinuxKernelVersion("6.5-35-generic"), LinuxKernelVersion("6.8-50-generic"),
                     LinuxKernelVersion("6.8-52-generic"), LinuxKernelVersion("6.8-57-generic"),
                     LinuxKernelVersion("5.15-91-generic")]
        expected_data = [LinuxKernelVersion("5.15-91-generic"), LinuxKernelVersion("5.15-133-generic"),
                         LinuxKernelVersion("5.15-134-generic"), LinuxKernelVersion("5.15-136-generic"),
                         LinuxKernelVersion("6.5-35-generic"), LinuxKernelVersion("6.8-50-generic"),
                         LinuxKernelVersion("6.8-52-generic"), LinuxKernelVersion("6.8-57-generic"),
                         LinuxKernelVersion("6.14-1-liquorix-amd64")]
        test_data.sort()
        self.assertEqual(test_data, expected_data)


# https://tproger.ru/translations/demystifying-decorators-in-python/

# https://devblogs.microsoft.com/oldnewthing/20050201-00/?p=36553
# https://stackoverflow.com/a/43512141
# https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-osversioninfoexa#remarks
class CurrentOs:
    @staticmethod
    def is_windows():
        # https://docs.python.org/3/library/sys.html#sys.platform
        return sys.platform.lower().startswith('win')

    # fixme utopia Что вернёт uname -r?
    @staticmethod
    def is_msys():
        # https://docs.python.org/3/library/sys.html#sys.platform
        return sys.platform.lower().startswith('msys')

    @staticmethod
    def is_linux():
        # https://docs.python.org/3/library/sys.html#sys.platform
        return sys.platform.lower().startswith('linux')

    @staticmethod
    def is_termux():
        # https://termux.dev/en/
        return CurrentOs.is_android()

    @staticmethod
    def is_android():
        try:
            cmd_result = subprocess.run("uname -o", shell=True, capture_output=True, text=True)
            if cmd_result.returncode:
                return False
            return cmd_result.stdout.lower().startswith("android")
        except Exception:
            return False

    @staticmethod
    def get_linux_kernel_version():
        if not CurrentOs.is_linux():
            return None
        # https://docs.python.org/3/library/os.html#os.uname
        return LinuxKernelVersion(platform.release())

    @staticmethod
    def get_windows_version():
        if not CurrentOs.is_windows():
            return None
        os_version_info_ex = sys.getwindowsversion()
        # fixme utopia Добавить информацию про wProductType
        return semantic_version.Version(major=os_version_info_ex.major, minor=os_version_info_ex.minor,
                                        build=os_version_info_ex.build)

    @staticmethod
    def is_ubuntu_or_like():
        return CurrentOs.__is_linux_distro_or_like("ubuntu")

    @staticmethod
    def is_debian_or_like():
        return CurrentOs.__is_linux_distro_or_like("debian")

    @staticmethod
    def is_arch_or_like():
        return CurrentOs.__is_linux_distro_or_like("arch")

    @staticmethod
    def __is_linux_distro_or_like(linux_distro_id):
        try:
            if not CurrentOs.is_linux():
                return False

            linux_distro_id = linux_distro_id.strip().lower()
            current_linux_distro_info = os_release.current_release()
            return (linux_distro_id == current_linux_distro_info.id) or (
                    linux_distro_id in current_linux_distro_info.id_like)
        except Exception as ex:
            return False

    @staticmethod
    def get_linux_distro_name():
        if not CurrentOs.is_linux():
            return None
        # https://pypi.org/project/os-release/
        # https://www.freedesktop.org/software/systemd/man/os-release.html
        return os_release.current_release().id

    @staticmethod
    def get_linux_distro_version():
        if not CurrentOs.is_linux():
            return None
        # https://pypi.org/project/os-release/
        # https://www.freedesktop.org/software/systemd/man/os-release.html
        return semantic_version.Version(version_string=os_release.current_release().version_id)

    # fixme utopia Проверить на Ubuntu 32bit
    # https://askubuntu.com/questions/768415/where-can-i-find-32-bit-version-of-ubuntu
    @staticmethod
    def is32bit():
        return platform.architecture()[0].lower() == "32bit"

    @staticmethod
    def is64bit():
        # https://www.fastwebhost.in/blog/how-to-find-if-linux-is-running-on-32-bit-or-64-bit/
        # https://wiki.termux.com/wiki/FAQ
        return platform.architecture()[0].lower() == "64bit"

    # https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/boot-to-uefi-mode-or-legacy-bios-mode?view=windows-11
    # https://www.hindicodingcommunity.com/2023/02/how-to-check-whether-secure-boot-is.html
    # https://www.ninjaone.com/blog/confirm-if-secure-boot-is-enabled-or-disabled/
    # https://www.tenforums.com/tutorials/85195-check-if-windows-10-using-uefi-legacy-bios.html
    # https://stackoverflow.com/questions/65314573/how-to-check-device-boot-mode-uefi-or-legacy
    # https://stackoverflow.com/questions/18172197/programmatically-determine-if-windows-8-secure-boot-is-enabled
    # https://learn.microsoft.com/en-us/powershell/module/secureboot/?view=windowsserver2025-ps
    @staticmethod
    def is_bios_boot():
        if CurrentOs.is_linux():
            return not Path("sys/firmware/efi").exists()
        elif CurrentOs.is_windows():
            return False
        return False

    @staticmethod
    def is_uefi_boot():
        if CurrentOs.is_linux():
            return Path("sys/firmware/efi").exists()
        elif CurrentOs.is_windows():
            return False
        return False

    # https://wiki.debian.org/SecureBoot#What_is_UEFI_Secure_Boot.3F
    # https://wiki.archlinux.org/title/Unified_Extensible_Firmware_Interface/Secure_Boot#Checking_Secure_Boot_status
    @staticmethod
    def is_uefi_secure_boot(self):
        return CurrentOs.is_uefi_boot() and False


class LinuxKernel:
    LIQUORIX_KERNEL_SETUP_SCRIPT_URL = "https://liquorix.net/install-liquorix.sh"

    def __init__(self):
        pass

    # https://liquorix.net/
    def download_and_install_liquorix_kernel(self):
        if not CurrentOs.is_linux():
            raise Exception(f"[LinuxKernel] Non Linux OS")

        if CurrentOs.is_debian_or_like() or CurrentOs.is_ubuntu_or_like() or CurrentOs.is_arch_or_like():
            response = requests.get(self.LIQUORIX_KERNEL_SETUP_SCRIPT_URL, stream=True)
            fp = tempfile.NamedTemporaryFile(delete=False)
            try:
                for chunk in response.iter_content(chunk_size=2 ** 16):
                    fp.write(chunk)
                fp.close()
                pathlib.Path(fp.name).chmod(0o777)
                subprocess.check_call(fp.name, shell=True)
            finally:
                fp.close()
                pathlib.Path(fp.name).unlink(missing_ok=True)
        else:
            raise Exception(
                f"[LinuxKernel] Install liquorix kernel NOT SUPPORTED for {CurrentOs.get_linux_distro_name()}")


class Platform:
    CHASSIS_TYPE_DESKTOP = 3
    CHASSIS_TYPE_LOW_PROFILE_DESKTOP = 4
    CHASSIS_TYPE_PIZZA_BOX = 5
    CHASSIS_TYPE_MINI_TOWER = 6
    CHASSIS_TYPE_TOWER = 7
    CHASSIS_TYPE_PORTABLE = 8
    CHASSIS_TYPE_LAPTOP = 9
    CHASSIS_TYPE_NOTEBOOK = 10
    CHASSIS_TYPE_HAND_HELD = 11
    CHASSIS_TYPE_DOCKING_STATION = 12
    CHASSIS_TYPE_ALL_IN_ONE = 13
    CHASSIS_TYPE_SUB_NOTEBOOK = 14
    CHASSIS_TYPE_SPACE_SAVING = 15
    CHASSIS_TYPE_LUNCH_BOX = 16
    CHASSIS_TYPE_MAIN_SYSTEM_CHASSIS = 17
    CHASSIS_TYPE_EXPANSION_CHASSIS = 18
    CHASSIS_TYPE_SUB_CHASSIS = 19
    CHASSIS_TYPE_BUS_EXPANSION_CHASSIS = 20
    CHASSIS_TYPE_PERIPHERAL_CHASSIS = 21
    CHASSIS_TYPE_STORAGE_CHASSIS = 22
    CHASSIS_TYPE_RACK_MOUNT_CHASSIS = 23
    CHASSIS_TYPE_SEALED_CASE_PC = 24

    def __init__(self):
        pass

    def is_laptop(self):
        return self.get_chassis_type() in [self.CHASSIS_TYPE_PORTABLE,
                                           self.CHASSIS_TYPE_LAPTOP,
                                           self.CHASSIS_TYPE_NOTEBOOK,
                                           self.CHASSIS_TYPE_SUB_NOTEBOOK]

    def get_chassis_type(self):
        if CurrentOs.is_linux():
            return int(pathlib.Path("/sys/devices/virtual/dmi/id/chassis_type").read_text())
        elif CurrentOs.is_windows():
            # https://stackoverflow.com/questions/55184682/powershell-getting-chassis-types-info
            return None
        else:
            return None


# fixme utopia Проверить на многопроцессорных системах (у меня есть)
class Cpu(BaseParser):
    # https://gcc.gnu.org/git/?p=gcc.git;a=blob;f=gcc/common/config/i386/cpuinfo.h;h=a6ede14a3ccb9f5e5eaa8866e2f29c35d3234285;hb=HEAD
    # https://codeberg.org/smxi/inxi/src/branch/master/inxi#L12095
    # https://github.com/torvalds/linux/blob/master/arch/x86/events/intel/core.c#L6527
    # https://en.wikichip.org/wiki/intel/microarchitectures
    # https://en.wikipedia.org/wiki/CPUID
    # https://www.etallen.com/cpuid.html

    __CPU_VENDOR = "vendor"
    __CPU_UARCH = "uarch"
    __CPU_UARCH_FAMILY = "uarch_family"
    __CPU_TECHNICAL_PROCESS = "technical_process"

    __TABLE = {__CPU_VENDOR: {"type": StringAsciiLetter, "default": None},
               __CPU_UARCH: {"type": StringAsciiWords, "default": None},
               __CPU_UARCH_FAMILY: {"type": StringAsciiWords, "default": None},
               __CPU_TECHNICAL_PROCESS: {"type": String, "default": None}}

    __CMD_LINE = "cpuid -1"

    # Микроархитектуры CPU расположены в хронологическом порядке появления на свет
    INTEL_UARCH_TABLE = [{"family": 0x06, "uarch_family": "P6 Pentium II"},
                         {"family": 0x06, "uarch_family": "P6 Pentium III"},
                         {"family": 0x06, "uarch_family": "P6 Pentium M"},
                         {"family": 0x06, "uarch": "Dothan"},
                         # https://www.intel.com/content/www/us/en/ark/products/codename/2643/products-formerly-dothan.html
                         {"family": 0x06, "uarch": "Yonah"},
                         # https://www.intel.com/content/www/us/en/ark/products/codename/2673/products-formerly-yonah.html
                         {"family": 0x06, "uarch": "Merom"},
                         # https://www.intel.com/content/www/us/en/ark/products/codename/2683/products-formerly-merom.html
                         {"family": 0x06, "uarch": "Penryn"},
                         # https://www.intel.com/content/www/us/en/ark/products/codename/26543/products-formerly-penryn.html
                         {"family": 0x06, "uarch": "Bonnell"},
                         {"family": 0x06, "uarch": "Nehalem"},
                         {"family": 0x06, "uarch": "Westmere"},
                         {"family": 0x06, "uarch": "Sandy Bridge",
                          "core_name_list": ["Sandy Bridge M", "Sandy Bridge", "Sandy Bridge E"]},
                         # https://www.intel.com/content/www/us/en/ark/products/codename/29900/products-formerly-sandy-bridge.html
                         {"family": 0x06, "uarch": "Saltwell"},
                         # https://en.wikichip.org/wiki/intel/microarchitectures/saltwell
                         # https://www.intel.com/content/www/us/en/ark/products/codename/43824/penwell.html
                         # https://www.intel.com/content/www/us/en/ark/products/codename/60105/products-formerly-centerton.html

                         {"family": 0x06, "uarch": "Ivy Bridge"},
                         {"family": 0x06, "uarch": "Silvermont"},
                         {"family": 0x06, "uarch": "Haswell",
                          "core_name_list": ["Haswell DT", "Haswell MB", "Haswell H", "Haswell ULT", "Haswell ULX",
                                             "Haswell EP", "Haswell EX", "Haswell E"]},
                         # https://www.intel.com/content/www/us/en/ark/products/codename/42174/products-formerly-haswell.html

                         {"family": 0x06, "uarch": "Knights Landing", "core_name_list": ["Knights Landing"]},
                         # https://www.intel.com/content/www/us/en/ark/products/codename/48999/products-formerly-knights-landing.html

                         {"family": 0x06, "uarch": "Broadwell",
                          "core_name_list": ["Broadwell Y", "Broadwell U", "Broadwell H", "Broadwell DT",
                                             "Broadwell EP", "Broadwell EX", "Broadwell E"]},
                         # https://www.intel.com/content/www/us/en/ark/products/codename/38530/products-formerly-broadwell.html
                         {"family": 0x06, "uarch": "Airmont"},
                         {"family": 0x06, "uarch": "Skylake"},
                         {"family": 0x06, "uarch": "Kaby Lake"},
                         {"family": 0x06, "uarch": "Goldmont"},
                         {"family": 0x06, "uarch": "Coffee Lake"},
                         {"family": 0x06, "uarch": "Goldmont Plus"},
                         {"family": 0x06, "uarch": "Knights Mill"},
                         {"family": 0x06, "uarch": "Palm Cove", "core_name_list": ["Cannon Lake U"]},
                         # https://www.intel.com/content/www/us/en/products/sku/136863/intel-core-i38121u-processor-4m-cache-up-to-3-20-ghz/specifications.html
                         {"family": 0x06, "uarch": "Cascade Lake"},
                         {"family": 0x06, "uarch": "Tremont", "core_name_list": ["Lakefield", "Snow Ridge"]},
                         # https://www.intel.com/content/www/us/en/ark/products/codename/81657/products-formerly-lakefield.html
                         # https://www.intel.com/content/www/us/en/ark/products/codename/87586/products-formerly-snow-ridge.html

                         {"family": 0x06, "uarch": "Sunny Cove", "core_name_list": ["Lakefield"]},
                         {"family": 0x06, "uarch": "Willow Cove",
                          "core_name_list": ["Tiger Lake Y", "Tiger Lake U", "Tiger Lake H35", "Tiger Lake H"]},
                         {"family": 0x06, "uarch": "Cooper Lake",
                          "core_name_list": ["Cooper Lake X", "Cooper Lake W", "Cooper Lake SP", "Cooper Lake AP"]},
                         # https://www.intel.com/content/www/us/en/ark/products/codename/189143/products-formerly-cooper-lake.html
                         {"family": 0x06, "uarch": "Gracemont"},
                         {"family": 0x06, "uarch": "Cypress Cove",
                          "core_name_list": ["Rocket Lake S", "Rocket Lake U"]},
                         # https://www.intel.com/content/www/us/en/ark/products/codename/192985/products-formerly-rocket-lake.html
                         {"family": 0x06, "uarch": "Golden Cove"},
                         {"family": 0x06, "uarch": "Raptor Cove"},
                         {"family": 0x06, "uarch": "Sapphire Rapids"},
                         {"family": 0x06, "uarch": "Emerald Rapids"},
                         {"family": 0x06, "uarch": "Redwood Cove"},
                         {"family": 0x06, "uarch": "Granite Rapids"},
                         {"family": 0x06, "uarch": "Sierra Forest"},
                         {"family": 0x06, "uarch": "Lion Cove", "core_name_list": ["Lunar Lake"]},
                         {"family": 0x06, "uarch": "Skymont", "core_name_list": ["Lunar Lake"]},
                         {"family": 0x06, "uarch": "Crestmont",
                          "core_name_list": ["Meteor Lake M", "Meteor Lake N", "Meteor Lake S"]},
                         {"family": 0x06, "uarch": "Redwood Cove",
                          "core_name_list": ["Meteor Lake M", "Meteor Lake N", "Meteor Lake S"]},
                         {"family": 0x06, "uarch": "Cougar Cove", "core_name_list": ["Panther Lake"]},
                         {"family": 0x06, "uarch": "Darkmont", "core_name_list": ["Panther Lake"]}
                         ]

    def __init__(self, cpuid_info=None):
        super(Cpu, self).__init__(self.__TABLE)
        if cpuid_info is None:  # Создать умолчательный объект
            return

        if self.copy_if(cpuid_info):  # Копирующий конструктор (в том числе если pci_address - это словарь)
            return

        # Создать объект из результата разбора выхлопа cpuid
        if self.init_fields(re.compile(Cpu.__get_regex(), flags=re.MULTILINE), cpuid_info):
            return

        raise Exception(f"[Cpu] Format FAIL: {cpuid_info} | {type(cpuid_info)}")

    def is_intel_above_sandybridge(self):
        return self.__is_intel_above_uarch_codename("Sandy Bridge")

    def is_intel_above_broadwell(self):
        return self.__is_intel_above_uarch_codename("Broadwell")

    def is_intel_integrated_vga_iris_xe(self):
        return self.__is_intel_above_uarch_codename("Willow Cove")

    def is_intel(self):
        return self.__is_cpu_vendor("intel")

    def is_amd(self):
        return self.__is_cpu_vendor("amd")

    def is_virtualization_support(self):
        try:
            if self.is_intel() or self.is_amd():
                # fixme utopia Проверить на процессорах AMD
                return "vmx" in cpuinfo.get_cpu_info()["flags"]
            else:
                return False
        except Exception as ex:
            return False

    @staticmethod
    def get_cpu0():
        if Cpu.__is_x86_compatible() or Cpu.__is_ia64_compatible():
            return Cpu(Cpu.__run_cpuid())
        else:
            raise Exception("[Cpu] Not support")

    def __is_cpu_vendor(self, target_cpu_vendor):
        try:
            if self.vendor is None:
                return False
            return Cpu.__trim_and_lower(target_cpu_vendor) in Cpu.__trim_and_lower(self.vendor)
        except Exception:
            return False

    @staticmethod
    def __run_cpuid():
        cmd_result = subprocess.run(Cpu.__CMD_LINE, shell=True, capture_output=True, text=True)
        if cmd_result.returncode:
            return ""
        return cmd_result.stdout

    @staticmethod
    def __get_regex():
        tmp = Cpu()
        result = "\(uarch synth\) ="
        result += f" {tmp.get_regex_for(Cpu.__CPU_VENDOR)}"
        result += f"(?: {tmp.get_regex_for(Cpu.__CPU_UARCH)})?"
        result += f"(?> \\{{{tmp.get_regex_for(Cpu.__CPU_UARCH_FAMILY)}\\}})?"
        result += f"(?>, {tmp.get_regex_for(Cpu.__CPU_TECHNICAL_PROCESS)})?"
        result += f"$"
        return result

    @staticmethod
    def __is_x86_compatible():
        return platform.machine().strip().lower() in ["i386", "i686", "x86_64"]

    @staticmethod
    def __is_ia64_compatible():
        return platform.machine().strip().lower() in ["ia64"]

    def __is_intel_above_uarch_codename(self, target_uarch, target_uarch_family=None):
        if not self.is_intel():
            return False

        return self.__get_uarch_index(self.INTEL_UARCH_TABLE, self.uarch,
                                      self.uarch_family) >= self.__get_uarch_index(self.INTEL_UARCH_TABLE,
                                                                                   target_uarch,
                                                                                   target_uarch_family)

    def __get_uarch_index(self, uarch_table, target_uarch, target_uarch_family=None):
        result = 0
        target_uarch = Cpu.__trim_and_lower(target_uarch)
        target_uarch_family = Cpu.__trim_and_lower(target_uarch_family)

        for item in uarch_table:
            if target_uarch is None:
                if target_uarch_family is not None:
                    uarch_family = Cpu.__trim_and_lower(item.get(self.__CPU_UARCH_FAMILY))
                    if uarch_family is not None and uarch_family in target_uarch_family:
                        break
            else:
                uarch = Cpu.__trim_and_lower(item.get(self.__CPU_UARCH))
                if uarch is not None and uarch in target_uarch:
                    break
            result += 1
        return result

    @staticmethod
    def __trim_and_lower(value):
        if value is None:
            return value
        return str(value).strip().lower()


class UnitTest_Cpu(unittest.TestCase):

    def test(self):
        ref_table = [
            (Cpu, "",
             {"is_exception": True}),
            (Cpu, "Hello world",
             {"is_exception": True}),
            (Cpu, 17,
             {"is_exception": True}),
            (Cpu,
             "   (multi-processing synth) = multi-core (c=2), hyper-threaded (t=2)\n   (multi-processing method) = Intel leaf 0xb\n   (APIC widths synth): CORE_width=3 SMT_width=1\n   (APIC synth): PKG_ID=0 CORE_ID=0 SMT_ID=1\n   (uarch synth) = Intel Sandy Bridge {Sandy Bridge}, 32nm\n   (synth) = Intel Core i*-2000 (Sandy Bridge D2/J1/Q0) {Sandy Bridge}, 32nm",
             {"expected": {"vendor": "Intel", "uarch": "Sandy Bridge", "uarch_family": "Sandy Bridge",
                           "technical_process": "32nm"},
              "is_exception": False,
              "expected_dict": {"vendor": "Intel", "uarch": "Sandy Bridge", "uarch_family": "Sandy Bridge",
                                "technical_process": "32nm"},
              "is_intel_above_sandybridge": True,
              "is_intel_above_broadwell": False,
              "is_intel_integrated_vga_iris_xe": False}),
            (Cpu,
             "   (uarch synth) = Intel Cooper Lake {optim of Cascade Lake, optim of Skylake}, 14nm++",
             {"expected": {"vendor": "Intel", "uarch": "Cooper Lake",
                           "uarch_family": "optim of Cascade Lake, optim of Skylake",
                           "technical_process": "14nm++"},
              "is_exception": False,
              "expected_dict": {"vendor": "Intel", "uarch": "Cooper Lake",
                                "uarch_family": "optim of Cascade Lake, optim of Skylake",
                                "technical_process": "14nm++"},
              "is_intel_above_sandybridge": True,
              "is_intel_above_broadwell": True,
              "is_intel_integrated_vga_iris_xe": True}),
            (Cpu,
             "   (uarch synth) = Intel {P6 Pentium II}, .35um",
             {"expected": {"vendor": "Intel", "uarch": None,
                           "uarch_family": "P6 Pentium II",
                           "technical_process": ".35um"},
              "is_exception": False,
              "expected_dict": {"vendor": "Intel", "uarch": None,
                                "uarch_family": "P6 Pentium II",
                                "technical_process": ".35um"},
              "is_intel_above_sandybridge": False,
              "is_intel_above_broadwell": False,
              "is_intel_integrated_vga_iris_xe": False}),
            (Cpu,
             "   (uarch synth) = Intel {P6 Pentium II}",
             {"expected": {"vendor": "Intel", "uarch": None,
                           "uarch_family": "P6 Pentium II",
                           "technical_process": None},
              "is_exception": False,
              "expected_dict": {"vendor": "Intel", "uarch": None,
                                "uarch_family": "P6 Pentium II",
                                "technical_process": None},
              "is_intel_above_sandybridge": False,
              "is_intel_above_broadwell": False,
              "is_intel_integrated_vga_iris_xe": False}),
        ]

        for class_type, initiate, test_data in ref_table:
            target = None
            try:
                target = class_type(initiate)
                self.assertFalse(test_data["is_exception"], f"No exception for \"{initiate}\"")
            except Exception as ex:
                self.assertTrue(test_data["is_exception"], f"Exception for \"{initiate}\": {ex}")

            if target is not None:
                self.assertEqual(target.get_fields_as_dict(), test_data["expected_dict"])
                self.assertEqual(target.is_intel_above_sandybridge(), test_data["is_intel_above_sandybridge"])
                self.assertEqual(target.is_intel_above_broadwell(), test_data["is_intel_above_broadwell"])
                self.assertEqual(target.is_intel_integrated_vga_iris_xe(), test_data["is_intel_integrated_vga_iris_xe"])


class Path:
    def __init__(self, path):
        self.__path = os.path.expanduser(os.path.expandvars(str(path)))

    @staticmethod
    def get_home_directory(user=getpass.getuser()):
        if CurrentOs.is_termux():
            user = ""

        result = Path(os.path.expanduser(f"~{user}"))
        if result.exists():
            return result
        return None

    def get(self):
        if os.path.isabs(self.__path):
            return self.__path
        this_script_dir = os.path.dirname(os.path.realpath(__file__))
        result = os.path.abspath(os.path.join(this_script_dir, self.__path))
        return result

    def get_filename(self):
        path = self.get()
        if os.path.isfile(path):
            return os.path.basename(path)
        return ""

    def get_dir_path(self):
        path = self.get()
        if os.path.isfile(path):
            return Path(os.path.dirname(path))
        return Path(path)

    def exists(self):
        return os.path.exists(self.get())

    def file_exists(self):
        return self.exists() and os.path.isfile(self.get())

    def exists_by_wildcard(self, wildcard):
        return bool(list(pathlib.Path(self.get()).glob(wildcard)))

    def makedirs(self):
        path = self.get()
        if os.path.isfile(path):
            raise Exception("Path \"{}\" is path to file, but should be a directory path".format(path))
        if os.path.isdir(path):
            # print("[WARNING] Path \"{}\" is path to exists directory".format(path))
            return
        os.makedirs(path)

    def copy_from(self, path):
        shutil.copy2(str(Path(path)), str(self))

    # fixme utopia backup для файла и для директории
    def create_backup(self, backup_file_path=None,
                      backup_prefix=f"unused_since_{datetime.datetime.now():%Y-%m-%dT%H_%M_%S_%f%z}_"):
        if not self.exists():
            return None

        if backup_file_path is None:
            backup_file_path = self.get_dir_path().join(f"{backup_prefix}{self.get_filename()}")
        else:
            backup_file_path = Path(backup_file_path)
        backup_file_path.copy_from(self.get())
        return backup_file_path

    # fixme utopia backup для файла и для директории
    def restore_from_backup(self, backup_file_path, is_remove_backup=False):
        backup_file_path_as_path = Path(backup_file_path)
        if not backup_file_path_as_path.exists():
            return False

        self.copy_from(backup_file_path_as_path)
        if bool(is_remove_backup):
            os.remove(str(backup_file_path_as_path))
        return True

    def join(self, path):
        return Path(os.path.join(self.get(), path))

    def add_executable(self):
        mode = os.stat(self.get()).st_mode
        mode |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        os.chmod(self.get(), mode)

    def __str__(self):
        return self.get()

    def __repr__(self):
        return self.__str__()


class TextConfigReader:
    def __init__(self, config_file_path, encoding="utf-8"):
        self.__config_file_path = Path(config_file_path)
        self.__encoding = str(encoding)

    def __str__(self):
        return str(self.__config_file_path)

    def __repr__(self):
        return self.__str__()

    def get(self):
        return self.__load_from_config()

    def exists(self):
        return self.__config_file_path.exists()

    def __load_from_config(self):
        result = ""
        with open(self.__config_file_path.get(), mode="rt", encoding=self.__encoding) as config_file:
            result += str(config_file.read())
        # print("Load from config: {}".format(result))
        return result


class TextConfigWriter:
    def __init__(self, config_file_path, encoding="utf-8", last_backup_file_path=None):
        self.__config_file_path = Path(config_file_path)
        self.__encoding = str(encoding)
        self.__last_backup_file_path = last_backup_file_path

    def __str__(self):
        return str(self.__config_file_path)

    def __repr__(self):
        return self.__str__()

    def set(self, data, set_executable=False):
        self.__makedirs()

        with open(self.__config_file_path.get(), mode="wt", encoding=self.__encoding) as config_file:
            config_file.write(str(data))

        if set_executable:
            self.__config_file_path.add_executable()
        return self.__config_file_path

    def set_with_backup(self, data, set_executable=False, is_rewrite_backup=False):
        if self.__config_file_path.exists():
            self.__last_backup_file_path = self.__config_file_path.create_backup(
                backup_file_path=self.__last_backup_file_path if is_rewrite_backup else None)
        self.set(data, set_executable)
        return self.get_last_backup_file_path()

    def get_last_backup_file_path(self):
        return self.__last_backup_file_path

    def restore_from_backup(self, is_remove_backup=False):
        if self.__last_backup_file_path is None or not self.__last_backup_file_path.exists():
            return False

        self.__config_file_path.restore_from_backup(self.get_last_backup_file_path(), is_remove_backup=is_remove_backup)

    def __makedirs(self):
        config_file_dir = os.path.dirname(self.__config_file_path.get())
        Path(config_file_dir).makedirs()


class JsonConfigWriter:
    def __init__(self, config_file_path, encoding="utf-8"):
        self.__text_config_writer = TextConfigWriter(config_file_path, encoding)

    def set(self, data):
        self.__text_config_writer.set(json.dumps(data, sort_keys=True, indent=4))


class JsonConfigReader:
    def __init__(self, config_file_path, encoding="utf-8"):
        self.__text_config_reader = TextConfigReader(config_file_path, encoding)
        self.__json_config_writer = JsonConfigWriter(config_file_path, encoding)

    def get(self):
        return json.loads(self.__text_config_reader.get())

    def get_or_create_if_non_exists(self, default_content_if_create=dict()):
        if not self.__text_config_reader.exists():
            self.__json_config_writer.set(default_content_if_create)
        return self.get()


class StunServerAddressList(JsonConfigReader):
    def __init__(self, config_file_path="stun-servers.config.json"):
        super().__init__(config_file_path)

    pass


class IpAddressAndPort:
    REGEX_PATTERN = r"([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}:[0-9]{1,5})"
    REGEX_PATTERN_PARSE = r"([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}):([0-9]{1,5})"

    def __init__(self, ip_address, port=None):
        if port is None:
            ip_address_and_port_as_str = str(ip_address)
            regex = re.compile(self.REGEX_PATTERN_PARSE)
            tmp = regex.findall(ip_address_and_port_as_str)
            if len(tmp) == 0:
                raise Exception("Parse ip_address_and_port FAIL: {}".format(ip_address_and_port_as_str))
            self.__ip_address = ipaddress.ip_address(tmp[0][0])
            self.__port = int(tmp[0][1])
        else:
            self.__ip_address = ipaddress.ip_address(ip_address)
            self.__port = int(port)

    def __str__(self):
        return "{}:{}".format(self.__ip_address, self.__port)

    def __repr__(self):
        return self.__str__()

    def get_ip_address(self):
        return self.__ip_address

    def get_port(self):
        return self.__port


class StunClient:
    STUN_RESPONSE_OK = 2
    REGEX_PATTERN = r"MappedAddress = {}".format(IpAddressAndPort.REGEX_PATTERN)
    STUN_CLIENT = "stun"

    def __init__(self, stun_server_address, local_port):
        self.__stun_server_address = stun_server_address
        self.__local_port = local_port

    def get_my_ip_address_and_port(self):
        result = self.__parse_stun_client_output(self.__run_client())
        if len(result) == 0:
            raise Exception("Stun client return NONE")
        return result[-1]

    def __run_client(self):
        result = subprocess.run(
            [self.STUN_CLIENT, self.__stun_server_address, "-v", "-p", str(self.__local_port)], capture_output=True,
            text=True
        )
        # print("Stun client return: {}".format(result))

        if result.returncode != self.STUN_RESPONSE_OK:
            raise Exception("Stun client call FAIL: {}".format(result.stderr))

        return result.stderr

    def __parse_stun_client_output(self, stun_client_output):
        regex = re.compile(self.REGEX_PATTERN)
        result_raw = regex.findall(stun_client_output)

        result = []
        for it in result_raw:
            result.append(IpAddressAndPort(it))

        return result


class StunClient2:
    STUN_PORT_DEFAULT = 3478

    def __init__(self, stun_server_address, local_port):
        self.__stun_server_address = stun_server_address
        self.__local_port = local_port

    def get_my_ip_address_and_port(self):
        stun_server_hostname, stun_server_port = self.__parse_stun_server_address()

        nat_type, my_ip_address, my_port = stun.get_ip_info(source_port=self.__local_port,
                                                            stun_host=stun_server_hostname, stun_port=stun_server_port)
        Logger.instance().debug(
            f"[StunClient] NAT type: {nat_type}\nUDP hole punching: {self.__nat_adapted_for_udp_hole_punching(nat_type)}")
        return IpAddressAndPort(my_ip_address, my_port)

    @staticmethod
    def __nat_adapted_for_udp_hole_punching(nat_type):
        # https://www.rfc-editor.org/rfc/rfc3489#section-10.1
        return (nat_type == stun.FullCone) or (nat_type == stun.RestricNAT) or (nat_type == stun.RestricPortNAT) or (
                nat_type == stun.OpenInternet)

    def __parse_stun_server_address(self):
        result = urllib.parse.urlparse(self.__stun_server_address, allow_fragments=False)
        hostname = result.hostname
        port = self.STUN_PORT_DEFAULT if result.port is None else int(result.port)
        Logger.instance().debug(f"[StunClient] STUN server: {hostname}:{port}")
        return hostname, port


class MyExternalIpAddressAndPort:
    def __init__(self, local_port):
        self.__local_port = local_port

    def get(self):
        stun_server_address_list = StunServerAddressList()
        for stun_server_address in stun_server_address_list.get():
            try:
                stun_client = StunClient2(stun_server_address, self.__local_port)
                result = stun_client.get_my_ip_address_and_port()
                Logger.instance().debug(f"[MyExternalIpAddressAndPort] {result}")
                return result
            except Exception as ex:
                Logger.instance().warning(f"[MyExternalIpAddressAndPort] FAIL (but we continue): {ex}")
        raise Exception("My external IP address and port NOT FOUND")


class OpenVpnServer:
    def __init__(self, config_file_path):
        self.__config_file_path = str(config_file_path)
        self.__runner = AsyncRunner()

    async def run(self):
        self.__runner.add(f"openvpn --config {self.__config_file_path}", shell=False)
        await self.__runner.run_all()


class OpenVpnClient:
    OPEN_VPN = "openvpn"

    def __init__(self, config_file_path):
        self.__config_file_path = str(config_file_path)

    def run(self):
        result = subprocess.run(
            [self.OPEN_VPN, "--config", self.__config_file_path],
            capture_output=True,
            text=True
        )
        Logger.instance().debug(f"[OpenVpnClient] Return: {result}")

        if result.returncode:
            raise Exception(f"[OpenVpnClient] Start FAIL: {result.stderr}")

        Logger.instance().debug("[OpenVpnClient] Start OK")


class TelegramBotConfig(JsonConfigReader):
    def __init__(self, config_file_path="telegram-bot.config.json"):
        super().__init__(config_file_path)

    pass


class TelegramClient:
    ENCODING = "utf-8"

    def __init__(self):
        self.__config = TelegramBotConfig().get()

    def send_message(self, message):
        with urllib.request.urlopen(self.__get_send_message_url(), data=self.__get_data(message)) as f:
            Logger.instance().debug(f"[TelegramClient] Send message: {f.read().decode(self.ENCODING)}")

    # https://core.telegram.org/bots/api#senddocument
    def send_file(self, file_path):
        _file_path = Path(file_path)
        files = {'document': (_file_path.get_filename(), open(_file_path.get(), 'rb'), "multipart/form-data")}
        response = requests.post(self.__get_send_document_url(), data={"chat_id": self.__config["chat_id"]},
                                 files=files)
        Logger.instance().debug(f"[TelegramClient] Send document: {response.content}")

    def __get_send_message_url(self):
        return self.__get_url("sendMessage")

    def __get_send_document_url(self):
        return self.__get_url("sendDocument")

    def __get_url(self, command):
        return "https://api.telegram.org/bot{}/{}".format(self.__config["bot_token"], command)

    def __get_data(self, message=None):
        body = {"chat_id": self.__config["chat_id"]}
        if message is not None:
            body.update({"text": str(message)})

        data = urllib.parse.urlencode(body)
        return data.encode(self.ENCODING)


# class UdpPing:
#     HPING = "hping3"
#
#     def __init__(self, ip_address_and_port, local_port):
#         self.__ip_address_and_port = ip_address_and_port
#         self.__local_port = local_port
#
#     def ping(self):
#
#     def __ping(self):
#         udp_mode_option = "-2"
#         verbose_mode_option = "-V"
#         packet_count_option = "--count {}".format(1)
#
#         result = subprocess.run(
#             [self.HPING, self.__stun_server_address, "-v", "-p", str(self.__local_port)], capture_output=True,
#             text=True
#         )
#         print("Stun client return: {}".format(result))


class OpenVpnConfig:
    def __init__(self, open_vpn_config_path="open-vpn.config.json"):
        self.__config_reader = JsonConfigReader(open_vpn_config_path)

    def get_server_name(self):
        return self.get_config_parameter_strong("open_vpn_server_name")

    def get_server_port(self):
        return int(self.get_config_parameter_strong("open_vpn_server_port"))

    def get_keys_dir(self):
        return self.get_config_parameter_strong("open_vpn_keys_dir")

    def get_server_logs_dir(self):
        return self.get_config_parameter_strong("open_vpn_server_logs_dir")

    def get_client_keys_dir(self):
        return self.get_config_parameter_strong("open_vpn_client_keys_dir")

    def get_client_logs_dir(self):
        return self.get_config_parameter_strong("open_vpn_client_logs_dir")

    def get_easy_rsa_version(self):
        return self.get_config_parameter_strong("easy_rsa_version")

    def get_my_current_ip_address_and_port(self):
        return self.get_config_parameter_strong("my_current_ip_address_and_port")

    def get_vm_bridge_ip_address_and_mask(self):
        return ipaddress.ip_interface(self.get_config_parameter_strong("vm_bridge_ip_address_and_mask"))

    def get_vm_registry_dir_path(self):
        return self.get_config_parameter_strong("vm_registry_dir_path")

    def get_internet_network_interface(self):
        result = self.get_config_parameter("internet_network_interface")
        if result is None:
            return result
        return NetworkInterface(result)

    @staticmethod
    def get_or_default_internet_network_interface(internet_network_interface_from_config):
        if internet_network_interface_from_config is None:
            result = NetworkInterface.get_internet_if()
            Logger.instance().debug(f"[OpenVpnConfig] Internet network interface: {result}")
            return result
        Logger.instance().debug(
            f"[OpenVpnConfig] Internet network interface SET MANUALLY: {internet_network_interface_from_config}")
        return NetworkInterface(internet_network_interface_from_config)

    def get_local_network_interface(self):
        result = self.get_config_parameter("local_network_interface")
        if result is None:
            return result
        return NetworkInterface(result)

    @staticmethod
    def get_or_default_local_network_interface(local_network_interface):
        if local_network_interface is None:
            result = NetworkInterface.get_internet_if()
            Logger.instance().debug(f"[OpenVpnConfig] Local network interface: {result}")
            return result
        Logger.instance().debug(f"[OpenVpnConfig] Local network interface SET MANUALLY: {local_network_interface}")
        return NetworkInterface(local_network_interface)

    def get_dns_config_dir_path(self):
        return self.get_config_parameter_strong("dns_config_dir_path")

    def get_dns_suffix(self):
        return self.get_config_parameter_strong("dns_suffix")

    def get_my_host(self):
        return self.get_config_parameter_strong("my_host")

    def get_virtio_win_drivers_url(self):
        return self.get_config_parameter_strong("virtio_win_drivers_url")

    def get_server_log_path(self):
        return os.path.join(self.get_server_logs_dir(), "server.log")

    def get_ca_cert_path(self):
        return os.path.join(self.get_keys_dir(), "ca.crt")

    def get_tls_auth_key_path(self):
        return os.path.join(self.get_keys_dir(), "ta.key")

    def get_dh_pem_path(self):
        return os.path.join(self.get_keys_dir(), "dh.pem")

    def get_server_cert_path(self):
        return os.path.join(self.get_keys_dir(), "{}.crt".format(self.get_server_name()))

    def get_server_key_path(self):
        return os.path.join(self.get_keys_dir(), "{}.key".format(self.get_server_name()))

    def get_ca_cert(self):
        return self._parse(TextConfigReader(self.get_ca_cert_path()).get(), "-----BEGIN CERTIFICATE-----",
                           "-----END CERTIFICATE-----")

    def get_tls_auth_key(self):
        return self._parse(TextConfigReader(self.get_tls_auth_key_path()).get(),
                           "-----BEGIN OpenVPN Static key V1-----",
                           "-----END OpenVPN Static key V1-----")

    def get_dh_pem(self):
        return self._parse(TextConfigReader(self.get_dh_pem_path()).get(),
                           "-----BEGIN DH PARAMETERS-----",
                           "-----END DH PARAMETERS-----")

    def get_server_cert(self):
        return self._parse(TextConfigReader(self.get_server_cert_path()).get(), "-----BEGIN CERTIFICATE-----",
                           "-----END CERTIFICATE-----")

    def get_server_key(self):
        return self._parse(TextConfigReader(self.get_server_key_path()).get(), "-----BEGIN PRIVATE KEY-----",
                           "-----END PRIVATE KEY-----")

    def get_config_parameter_strong(self, name):
        result = self.get_config_parameter(name)
        if result is None:
            raise Exception("Mandatory config parameter \"{}\" NOT FOUND".format(name))
        return result

    def get_config_parameter(self, name):
        result = self.__config_reader.get()[name]
        if result is None:
            return None
        return str(result)

    @staticmethod
    def _parse(config_as_string, begin_label, end_label):
        regex = re.compile(r"({}[\s\S]*{})".format(begin_label, end_label), re.MULTILINE)
        return regex.findall(config_as_string)[0]


class OpenVpnClientConfig(OpenVpnConfig):
    def __init__(self, user_name, open_vpn_config_path="open-vpn.config.json"):
        super().__init__(open_vpn_config_path)
        self.__user_name = user_name

    pass

    def get_client_log_path(self):
        return os.path.join(self.get_client_logs_dir(), "{}.log".format(self.__user_name))

    def get_client_cert_path(self):
        return os.path.join(self.get_client_keys_dir(), "{}.crt".format(self.__user_name))

    def get_client_key_path(self):
        return os.path.join(self.get_client_keys_dir(), "{}.key".format(self.__user_name))

    def get_client_cert(self):
        return super()._parse(TextConfigReader(self.get_client_cert_path()).get(), "-----BEGIN CERTIFICATE-----",
                              "-----END CERTIFICATE-----")

    def get_client_key(self):
        return super()._parse(TextConfigReader(self.get_client_key_path()).get(), "-----BEGIN PRIVATE KEY-----",
                              "-----END PRIVATE KEY-----")

    # fixme utopia Получить весь список пользователей
    # fixme utopia Сохранять вместе с логином пользователя telegram


class OpenVpnConfigKeyValue:
    def __init__(self):
        self.__container = []

    def add_default(self, key, value):
        as_xml = False
        self.__add(key, value, as_xml)

    def add(self, key, value):
        as_xml = False
        self.__add_with_replace(key, value, as_xml)

    def add_as_xml(self, key, value):
        as_xml = True
        self.__add_with_replace(key, value, as_xml)

    def render(self):
        result = ""
        for (key, value) in self.__container:
            result += self.__render_key_value(key, value)
        return result

    def __add_with_replace(self, key, value, as_xml):
        index = self.__get_key_index(key)
        if index is None:
            self.__add(key, value, as_xml)
        else:
            self.__container[index] = self.__build_key_value_as_tuple(key, value, as_xml)

    def __get_key_index(self, key):
        index = 0
        for (k, v) in self.__container:
            if k == key:
                return index
            index += 1
        return None

    def __add(self, key, value, as_xml):
        self.__container.append(self.__build_key_value_as_tuple(key, value, as_xml))

    @staticmethod
    def __build_key_value_as_tuple(key, value, as_xml):
        if value is None:
            return str(key), {"parameter_value": None, "as_xml": as_xml}
        else:
            return str(key), {"parameter_value": str(value), "as_xml": as_xml}

    @staticmethod
    def __render_key_value(key, value):
        parameter_value = value["parameter_value"]
        if bool(value["as_xml"]):
            if parameter_value is None:
                result = "<{0}></{0}>\n".format(key)
            else:
                result = "<{0}>\n{1}\n</{0}>\n".format(key, parameter_value)
        else:
            if parameter_value is None:
                result = "{}\n".format(key)
            else:
                result = "{} {}\n".format(key, parameter_value)
        return result


class OpenVpnServerConfigGenerator:
    def __init__(self, config_template_file_path="open-vpn-server.config.template",
                 output_config_dir="."):
        self.__config_template_reader = TextConfigReader(config_template_file_path)
        self.__key_value_config = OpenVpnConfigKeyValue()
        self.__open_vpn_config = OpenVpnConfig()
        self.__output_config_file = TextConfigWriter(
            os.path.join(str(output_config_dir), "server.ovpn"))

    def generate(self):
        return self.__output_config_file.set(self.__render_to_string())

    def __render_to_string(self):
        self.__generate()
        return self.__key_value_config.render()

    def __generate(self):
        self.__parse_template()
        self.__add_port()
        self.__add_key_direction()
        self.__add_ca_cert()
        self.__add_tls_auth_key()
        self.__add_dh_pem()
        self.__add_server_cert()
        self.__add_server_key()
        self.__add_server_log()
        # fixme utopia Если сетка виртуальных машин не настроена, не готовить конфиг?
        #  Или исключение от openvpn сервера обработать более корректно?
        # https://openvpn.net/community-resources/ethernet-bridging/
        # https://qna.habr.com/q/276200
        self.__add_client_route_to_vm_bridge_network()
        self.__add_dns_for_vm_bridge_network()

    def __parse_template(self):
        regex = re.compile(r"^[ \t]*([a-z\-_0-9]+)[ \t]*(.*)\n", re.MULTILINE)
        tmp = regex.findall(self.__config_template_reader.get())

        if len(tmp) == 0:
            raise Exception("Parse ip_address_and_port FAIL")  # fixme utopia text

        for t in tmp:
            self.__key_value_config.add_default(t[0], t[1])

    def __add_port(self):
        self.__key_value_config.add("port", self.__open_vpn_config.get_server_port())

    def __add_key_direction(self):
        self.__key_value_config.add("key-direction", 0)

    def __add_ca_cert(self):
        self.__key_value_config.add_as_xml("ca", self.__open_vpn_config.get_ca_cert())

    def __add_tls_auth_key(self):
        self.__key_value_config.add_as_xml("tls-auth", self.__open_vpn_config.get_tls_auth_key())

    def __add_dh_pem(self):
        self.__key_value_config.add_as_xml("dh", self.__open_vpn_config.get_dh_pem())

    def __add_server_cert(self):
        self.__key_value_config.add_as_xml("cert", self.__open_vpn_config.get_server_cert())

    def __add_server_key(self):
        self.__key_value_config.add_as_xml("key", self.__open_vpn_config.get_server_key())

    def __add_server_log(self):
        self.__key_value_config.add("log", self.__open_vpn_config.get_server_log_path())

        d = os.path.dirname(self.__open_vpn_config.get_server_log_path())
        if not os.path.exists(d):
            os.makedirs(d)

    def __add_client_route_to_vm_bridge_network(self):
        ip_network = self.__open_vpn_config.get_vm_bridge_ip_address_and_mask().network
        self.__key_value_config.add_default("push",
                                            "\"route {} {}\"".format(ip_network.network_address, ip_network.netmask))
        # self.__key_value_config.add_default("route", "{} {}".format(ip_network.network_address, ip_network.netmask))

    def __add_dns_for_vm_bridge_network(self):
        ip = self.__open_vpn_config.get_vm_bridge_ip_address_and_mask().ip
        self.__key_value_config.add_default("push", "\"dhcp-option DNS {}\"".format(ip))


class OpenVpnClientConfigGenerator:
    def __init__(self, ip_address_and_port, user_name,
                 config_template_file_path="open-vpn-client.config.template",
                 output_client_config_dir="."):
        self.__config_template_reader = TextConfigReader(config_template_file_path)
        self.__key_value_config = OpenVpnConfigKeyValue()
        self.__open_vpn_client_config = OpenVpnClientConfig(user_name)
        self.__output_config_file = TextConfigWriter(
            os.path.join(str(output_client_config_dir), "client-{}.ovpn".format(user_name)))
        self.__ip_address_and_port = ip_address_and_port

    def generate(self):
        return self.__output_config_file.set(self.__render_to_string())

    def __render_to_string(self):
        self.__generate()
        return self.__key_value_config.render()

    def __generate(self):
        self.__parse_template()
        self.__add_ip_address()
        self.__add_port()
        self.__add_key_direction()
        self.__add_ca_cert()
        self.__add_tls_auth_key()
        self.__add_client_cert()
        self.__add_client_key()
        self.__add_client_log()

    def __parse_template(self):
        regex = re.compile(r"^[ \t]*([a-z\-_0-9]+)[ \t]*(.*)\n", re.MULTILINE)
        tmp = regex.findall(self.__config_template_reader.get())

        if len(tmp) == 0:
            raise Exception("Parse ip_address_and_port FAIL")  # fixme utopia text

        for t in tmp:
            self.__key_value_config.add_default(t[0], t[1])

    def __add_ip_address(self):
        self.__key_value_config.add("remote", self.__ip_address_and_port.get_ip_address())

    def __add_port(self):
        self.__key_value_config.add("rport", self.__ip_address_and_port.get_port())

    def __add_key_direction(self):
        self.__key_value_config.add("key-direction", 1)

    def __add_ca_cert(self):
        self.__key_value_config.add_as_xml("ca", self.__open_vpn_client_config.get_ca_cert())

    def __add_tls_auth_key(self):
        self.__key_value_config.add_as_xml("tls-auth", self.__open_vpn_client_config.get_tls_auth_key())

    def __add_client_cert(self):
        self.__key_value_config.add_as_xml("cert", self.__open_vpn_client_config.get_client_cert())

    def __add_client_key(self):
        self.__key_value_config.add_as_xml("key", self.__open_vpn_client_config.get_client_key())

    def __add_client_log(self):
        self.__key_value_config.add("log", self.__open_vpn_client_config.get_client_log_path())

        d = os.path.dirname(self.__open_vpn_client_config.get_client_log_path())
        if not os.path.exists(d):
            os.makedirs(d)


class NetworkInterface:
    # https://developers.google.com/speed/public-dns/docs/using#addresses
    GOOGLE_PUBLIC_DNS_IPV4_1 = ipaddress.ip_address("8.8.8.8")
    GOOGLE_PUBLIC_DNS_IPV4_2 = ipaddress.ip_address("8.8.4.4")

    GOOGLE_PUBLIC_DNS_IPV6_1 = ipaddress.ip_address("2001:4860:4860:0:0:0:0:8888")
    GOOGLE_PUBLIC_DNS_IPV6_2 = ipaddress.ip_address("2001:4860:4860:0:0:0:0:8844")

    NAME_LENGTH_MIN = 1
    NAME_LENGTH_MAX = 16

    def __init__(self, name):
        self.__name = str(name)

    def __str__(self):
        return self.__name

    def __repr__(self):
        return self.__str__()

    @staticmethod
    def list():
        return list(psutil.net_if_addrs().keys())

    @staticmethod
    def get_internet_if_strong():
        result = NetworkInterface.get_internet_if()
        if result is None:
            raise Exception("Internet interface NOT FOUND")
        return result

    @staticmethod
    def get_internet_if():
        # https://unix.stackexchange.com/questions/473803/how-to-find-out-the-interface-which-is-being-used-for-internet

        cmd_result = subprocess.run("ip route get {}".format(NetworkInterface.GOOGLE_PUBLIC_DNS_IPV4_1), shell=True,
                                    capture_output=True, text=True)
        if cmd_result.returncode:
            raise Exception("Get internet network interface FAIL: {}".format(cmd_result))

        regex = re.compile(fr".* dev (\S{{{NetworkInterface.NAME_LENGTH_MIN},{NetworkInterface.NAME_LENGTH_MAX}}}) .*",
                           re.MULTILINE)
        tmp = regex.findall(cmd_result.stdout)
        if len(tmp) == 0:
            return None

        result = NetworkInterface(tmp[0])
        if not result.exists():
            return None

        return result

    def exists(self):
        return self.__name in self.list()

    def is_wireless(self):
        # https://www.linux.org.ru/forum/general/11160638
        # fixme utopia Реализовать
        return True

    def is_internet(self):
        return True

    def is_wired(self):
        # fixme utopia Реализовать
        return True

    def is_bridged(self):
        # fixme utopia Реализовать
        return True

    def get_ipv4_interface_if(self):
        for net_if_name, snicaddr_list in psutil.net_if_addrs().items():
            if net_if_name == self.__name:
                for family, address, netmask, broadcast, ptp in snicaddr_list:
                    if family == socket.AddressFamily.AF_INET:
                        return ipaddress.ip_interface("{}/{}".format(address, netmask))

        return None

    def get_ipv6_interface_if(self):
        for net_if_name, snicaddr_list in psutil.net_if_addrs().items():
            if net_if_name == self.__name:
                for family, address, netmask, broadcast, ptp in snicaddr_list:
                    if family == socket.AddressFamily.AF_INET6:
                        return ipaddress.ip_interface("{}".format(address))

        return None


class BridgeFirewall:
    """
    # @details см. https://wiki.gentoo.org/wiki/QEMU/Bridge_with_Wifi_Routing и https://wiki.gentoo.org/wiki/QEMU/Options#Virtual_network_cable_.28TAP.29
    """

    def __init__(self, bridge_if, internet_if, block_internet_access=False):
        if bridge_if is None or not bridge_if.exists():
            raise Exception("Bridge interface NOT FOUND")

        if internet_if is None or not internet_if.exists():
            raise Exception("Internet interface NOT FOUND")

        self.__bridge_name = str(bridge_if)
        self.__internet_if = internet_if
        self.__block_internet_access = block_internet_access

    def setup(self):
        self.__setup_filter_bridge_to_internet()
        self.__setup_nat_postrouting_masquerade()
        self.__setup_filter_internet_to_bridge()

    def clear(self):
        clear = True
        self.__setup_filter_bridge_to_internet(clear)
        self.__setup_nat_postrouting_masquerade(clear)
        self.__setup_filter_internet_to_bridge(clear)

    def clear_at_exit(self):
        try:
            self.clear()
        except Exception as ex:
            Logger.instance().error(f"[BridgeFirewall] FAIL: {ex}")

    def __setup_filter_bridge_to_internet(self, clear=False):
        # sudo iptables -t filter -A FORWARD -i {self.__bridge_name} -o {self.__internet_if_name} -j ACCEPT
        # sudo iptables -t filter -L -v -n

        table = iptc.Table(iptc.Table.FILTER)
        chain = iptc.Chain(table, "FORWARD")

        rule = iptc.Rule()
        rule.in_interface = self.__bridge_name
        rule.out_interface = str(self.__internet_if)
        target = iptc.Target(rule, "ACCEPT")
        rule.target = target

        if clear:
            chain.delete_rule(rule)
        else:
            chain.insert_rule(rule)
        table.commit()
        Logger.instance().debug(
            f"[BridgeFirewall] Table FILTER after setup {iptc.easy.dump_table(iptc.Table.FILTER, ipv6=False)}")

    def __setup_nat_postrouting_masquerade(self, clear=False):
        # sudo iptables -t nat -A POSTROUTING -o {self.__internet_if_name} -j MASQUERADE

        # Запретить выход в интернет
        # sudo iptables -t nat -A POSTROUTING -o wlp0s20f3 -d 192.168.0.0/24 -j MASQUERADE
        # sudo iptables -t nat -L -v -n

        table = iptc.Table(iptc.Table.NAT)
        chain = iptc.Chain(table, "POSTROUTING")

        rule = iptc.Rule()
        rule.out_interface = str(self.__internet_if)

        if self.__block_internet_access:
            rule.dst = str(self.__internet_if.get_ipv4_interface_if().network)

        target = iptc.Target(rule, "MASQUERADE")
        rule.target = target

        if clear:
            chain.delete_rule(rule)
        else:
            chain.insert_rule(rule)
        table.commit()
        Logger.instance().debug(
            f"[BridgeFirewall] Table NAT after setup {iptc.easy.dump_table(iptc.Table.NAT, ipv6=False)}")

    def __setup_filter_internet_to_bridge(self, clear=False):
        # sudo iptables -t filter -A FORWARD -i {self.__internet_if_name} -o {self.__bridge_name} -m state --state RELATED,ESTABLISHED -j ACCEPT
        # sudo iptables -t filter -L -v -n

        table = iptc.Table(iptc.Table.FILTER)
        chain = iptc.Chain(table, "FORWARD")

        rule = iptc.Rule()
        rule.in_interface = str(self.__internet_if)
        rule.out_interface = self.__bridge_name
        target = iptc.Target(rule, "ACCEPT")
        rule.target = target

        match = iptc.Match(rule, "state")
        match.state = "RELATED,ESTABLISHED"
        rule.add_match(match)

        if clear:
            chain.delete_rule(rule)
        else:
            chain.insert_rule(rule)
        table.commit()
        Logger.instance().debug(
            f"[BridgeFirewall] Table FILTER after setup {iptc.easy.dump_table(iptc.Table.FILTER, ipv6=False)}")


# https://en.wikipedia.org/wiki/Hostname
# Название должно полностью подчиняться правилам формирования host имени
# tolower case
# без точек в имени, dnsmasq их не понимает https://serverfault.com/a/229349
class VmName:
    # https://stackoverflow.com/questions/106179/regular-expression-to-match-dns-hostname-or-ip-address
    __REGEX = ""

    def __init__(self, name):
        self.__name = str(name)

    def __str__(self):
        return self.__name

    def __repr__(self):
        return self.__str__()


# https://stackoverflow.com/questions/17493307/creating-set-of-objects-of-user-defined-class-in-python
class VmMetaData:
    class Parameter(pathlib.Path):
        _flavour = type(pathlib.Path())._flavour

        def __new__(cls, name, parameter_dir_path, value_default_handler=lambda: None,
                    deserialize_handler=lambda x: str(x),
                    serialize_handler=lambda x: x,
                    encoding="UTF8", extension="txt"):
            instance = super(VmMetaData.Parameter, cls).__new__(cls, pathlib.Path(
                str(parameter_dir_path)).resolve() / f"{name}.{extension}")
            instance.__value_default_handler = value_default_handler
            instance.__deserialize_handler = deserialize_handler
            instance.__serialize_handler = serialize_handler
            instance.__encoding = encoding
            return instance

        def exists(self):
            return super(VmMetaData.Parameter, self).exists() and super(VmMetaData.Parameter, self).resolve().is_file()

        def raise_exception_if_non_exists(self):
            if not self.exists():
                raise Exception(f'[Vm] Parameter "{self.name}" in "{self}" NOT FOUND')

        def load(self):
            result = self.__value_default_handler() if self.__value_default_handler else None
            if self.exists():
                result = self.read_text(encoding=self.__encoding)
                if self.__deserialize_handler:
                    result = self.__deserialize_handler(result)
            elif result is not None:
                self.store(result)

            return result

        def store(self, value):
            self.parent.mkdir(parents=True, exist_ok=True)
            if self.__serialize_handler:
                value = self.__serialize_handler(value)
            self.write_text(str(value), encoding=self.__encoding)

    IMAGE_EXTENSION = "img"

    def __init__(self, name, image_dir_path):
        self.__image_path = VmMetaData.Parameter(VmName(name), image_dir_path, extension=self.IMAGE_EXTENSION)
        self.__mac_address = VmMetaData.Parameter("mac_address", image_dir_path,
                                                  value_default_handler=lambda: netaddr.EUI(str(randmac.RandMac())),
                                                  deserialize_handler=lambda x: netaddr.EUI(x),
                                                  serialize_handler=lambda x: netaddr.EUI(x))
        self.__ssh_forward_port = VmMetaData.Parameter("ssh_forward_port", image_dir_path,
                                                       deserialize_handler=lambda x: TcpPort(x),
                                                       serialize_handler=lambda x: TcpPort(x))
        self.__rdp_forward_port = VmMetaData.Parameter("rdp_forward_port", image_dir_path,
                                                       deserialize_handler=lambda x: TcpPort(x),
                                                       serialize_handler=lambda x: TcpPort(x))
        self.make_dirs()

    def __str__(self):
        return str(self.to_dict())

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        if other is self:
            return True
        elif isinstance(other, VmMetaData):
            return self.get_name() == other.get_name()
        else:
            return self.get_name() == str(other)

    def __hash__(self):
        return self.get_name().__hash__()

    def to_dict(self):
        return {"name": self.get_name(),
                "image_path": self.get_image_path(),
                "mac_address": self.get_mac_address(),
                "ssh_forward_port": self.get_ssh_forward_port(),
                "rdp_forward_port": self.get_rdp_forward_port()}

    def check_image_exists(self):
        return self.__image_path.raise_exception_if_non_exists()

    def get_name(self):
        return self.__image_path.stem

    def get_image_path(self):
        return pathlib.Path(self.__image_path)

    def image_exists(self):
        return self.__image_path.exists()

    def get_mac_address(self):
        return self.get_mac_address_path().load()

    def get_mac_address_path(self):
        return self.__mac_address

    def get_mac_address_as_string(self):
        result = self.get_mac_address()
        result.dialect = netaddr.mac_unix_expanded
        return str(result)

    def get_hostname(self):
        return self.get_name()

    ## Получить IP адрес запущенной виртуальной машины
    # @warning IP адрес виртуальной машине раздаётся через DHCP, поэтому до запуска виртуальной машины понять её IP адрес нельзя
    # @return IP адрес запущенной виртуальной машины или исключение, если не удалось получить результат
    def get_ip_address_strong(self):
        return ipaddress.ip_address(socket.gethostbyname(self.get_hostname()))

    def get_ip_address(self):
        try:
            return self.get_ip_address_strong()
        except Exception:
            return None

    def get_ssh_forward_port(self):
        return self.get_ssh_forward_port_path().load()

    def get_ssh_forward_port_path(self):
        return self.__ssh_forward_port

    def set_ssh_forward_port(self, ssh_forward_port):
        self.get_ssh_forward_port_path().store(ssh_forward_port)

    def get_rdp_forward_port(self):
        return self.get_rdp_forward_port_path().load()

    def get_rdp_forward_port_path(self):
        return self.__rdp_forward_port

    def set_rdp_forward_port(self, rdp_forward_port):
        self.get_rdp_forward_port_path().store(rdp_forward_port)

    def get_working_dir_path(self):
        return self.get_image_path().parent / "data"

    def make_dirs(self):
        self.__image_path.parent.mkdir(parents=True, exist_ok=True)
        self.get_working_dir_path().mkdir(parents=True, exist_ok=True)


class UnitTest_VmMetaData(unittest.TestCase):
    def test_mac_address(self):
        vm_name = "test"

        with tempfile.TemporaryDirectory() as temp_dir_path:
            vm_meta_data = VmMetaData(vm_name, temp_dir_path)

            self.assertEqual(vm_meta_data.get_name(), vm_name)
            self.assertIsInstance(vm_meta_data.get_name(), str)
            self.assertEqual(vm_meta_data.get_hostname(), vm_name)
            self.assertIsInstance(vm_meta_data.get_hostname(), str)

            self.assertEqual(vm_meta_data.get_image_path(),
                             pathlib.Path(temp_dir_path) / f"{vm_name}.{VmMetaData.IMAGE_EXTENSION}")
            self.assertIsInstance(vm_meta_data.get_image_path(), pathlib.Path)
            self.assertFalse(vm_meta_data.image_exists())
            self.assertIsInstance(vm_meta_data.image_exists(), bool)

            self.assertRaises(Exception, vm_meta_data.check_image_exists)

            # MAC адрес генерируется и сохраняется на диске, поэтому повторный вызов get_mac_address()
            # вернёт тот же результат что и первый вызов
            mac_address1 = vm_meta_data.get_mac_address()
            mac_address2 = vm_meta_data.get_mac_address()
            self.assertEqual(mac_address1, mac_address2)
            self.assertEqual(netaddr.EUI(vm_meta_data.get_mac_address_as_string()), mac_address1)
            self.assertIsInstance(vm_meta_data.get_mac_address(), netaddr.EUI)
            self.assertIsInstance(vm_meta_data.get_mac_address_as_string(), str)

            self.assertEqual(vm_meta_data.get_ssh_forward_port(), None)
            self.assertEqual(vm_meta_data.get_rdp_forward_port(), None)

            self.assertTrue(vm_meta_data.get_working_dir_path().exists())
            self.assertIsInstance(vm_meta_data.get_working_dir_path(), pathlib.Path)

            mac_address_expected = "fd:63:8b:12:6f:5b"
            vm_meta_data.get_mac_address_path().store(mac_address_expected)
            self.assertEqual(vm_meta_data.get_mac_address(), netaddr.EUI(mac_address_expected))

            ssh_forward_port_expected = 111
            vm_meta_data.set_ssh_forward_port(ssh_forward_port_expected)
            self.assertEqual(vm_meta_data.get_ssh_forward_port(), TcpPort(ssh_forward_port_expected))
            self.assertIsInstance(vm_meta_data.get_ssh_forward_port(), TcpPort)

            rdp_forward_port_expected = 222
            vm_meta_data.set_rdp_forward_port(rdp_forward_port_expected)
            self.assertEqual(vm_meta_data.get_rdp_forward_port(), TcpPort(rdp_forward_port_expected))
            self.assertIsInstance(vm_meta_data.get_rdp_forward_port(), TcpPort)

    def test_equal(self):
        with tempfile.TemporaryDirectory() as temp_dir_path:
            vm_meta_data1 = VmMetaData("test", temp_dir_path)
            self.assertEqual(vm_meta_data1, vm_meta_data1)

            vm_meta_data2 = VmMetaData("test", temp_dir_path)
            self.assertEqual(vm_meta_data1, vm_meta_data2)

            vm_meta_data3 = VmMetaData("test3", temp_dir_path)
            self.assertNotEqual(vm_meta_data1, vm_meta_data3)
            self.assertNotEqual(vm_meta_data2, vm_meta_data3)

            vm_meta_data_set = {vm_meta_data1, vm_meta_data2, vm_meta_data3}
            self.assertEqual(len(vm_meta_data_set), 2)

            self.assertTrue(vm_meta_data1 in vm_meta_data_set)
            self.assertTrue(vm_meta_data2 in vm_meta_data_set)
            self.assertTrue(vm_meta_data3 in vm_meta_data_set)


class VmRegistry:
    __IMAGE_FORMAT = "qcow2"

    def __init__(self, vm_registry_dir_path):
        self.__vm_registry_dir_path = pathlib.Path(str(Path(vm_registry_dir_path))).resolve()

    def create(self, name, image_size_in_gib=20):
        result = self.get(name)
        if result:
            raise Exception(
                f'[Vm] Image "{result.get_image_path()}" EXISTS. Please change VM name')
        else:
            result = VmMetaData(name, self.__vm_registry_dir_path / name)

        command_line = self.__create_image_command_line(result, image_size_in_gib)
        Logger.instance().debug(f"[Vm] Create image cmd: {command_line}")
        subprocess.check_call(command_line, shell=True)
        return result

    def list(self):
        result = set()
        if not self.__vm_registry_dir_path.exists() or not self.__vm_registry_dir_path.is_dir():
            return result

        for path in self.__vm_registry_dir_path.iterdir():
            if path.is_dir() or path.resolve().is_dir():
                vm_meta_data = VmMetaData(path.name, path)
                if vm_meta_data.image_exists():
                    result.add(vm_meta_data)
        return result

    def get_with_verifying(self, name):
        result = self.get(name)
        if not result:
            raise Exception(f'[Vm] Image "{name}" NOT FOUND')
        return result

    def get(self, name):
        for vm_meta_data in self.list():
            if vm_meta_data == name:
                return vm_meta_data
        return None

    def set_ssh_forward_port(self, name, ssh_forward_port):
        meta_data = self.get_with_verifying(name)
        meta_data.set_ssh_forward_port(ssh_forward_port)

    def set_rdp_forward_port(self, name, rdp_forward_port):
        meta_data = self.get_with_verifying(name)
        meta_data.set_rdp_forward_port(rdp_forward_port)

    def __create_image_command_line(self, vm_meta_data, image_size_in_gib):
        return f'qemu-img create -f {self.__IMAGE_FORMAT} "{vm_meta_data.get_image_path()}" {image_size_in_gib}G'


# https://man7.org/linux/man-pages/man5/resolv.conf.5.html
class ResolvConf:
    __SPACE_SYMBOLS = "[\t ]"
    __SPACE_SYMBOLS_ZERO_OR_MORE = f"{__SPACE_SYMBOLS}*"
    __SPACE_SYMBOLS_ONE_OR_MORE = f"{__SPACE_SYMBOLS}+"
    __IP_ADDRESS_REGEX = r"[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}"
    __NAMESERVER = "nameserver"

    def __init__(self, resolv_conf_path="/etc/resolv.conf"):
        self.__reader = TextConfigReader(resolv_conf_path)
        self.__writer = TextConfigWriter(resolv_conf_path)
        self.__content = str()

    def add_nameserver_if(self, nameserver_ip_address):
        target_ip_address = ipaddress.ip_address(nameserver_ip_address)

        if target_ip_address in self.get_nameserver_list():
            return

        self.__content += f"\n{self.__NAMESERVER} {target_ip_address}"
        self.__save()

    def remove_nameserver(self, nameserver_ip_address):
        target_ip_address = ipaddress.ip_address(nameserver_ip_address)

        self.__load()
        regex = re.compile(self.__build_nameserver_remover_regex(target_ip_address), re.MULTILINE)
        empty_line = ""
        self.__content = regex.sub(empty_line, self.__content)
        self.__save()

    def get_nameserver_list(self):
        self.__load()
        regex = re.compile(self.__build_nameserver_search_regex(), re.MULTILINE)
        tmp = regex.findall(self.__content)

        result = set()
        for t in tmp:
            result.add(ipaddress.ip_address(t))
        return result

    def __load(self):
        self.__content = self.__reader.get()

    def __save(self):
        self.__writer.set(self.__content)

    def __build_nameserver_search_regex(self):
        return self.__build_basic_regex(f"({self.__IP_ADDRESS_REGEX})")

    def __build_nameserver_remover_regex(self, target_nameserver_ip_address):
        return f"({self.__build_basic_regex(str(target_nameserver_ip_address))})"

    def __build_basic_regex(self, value, parameter=__NAMESERVER):
        return f"^{self.__SPACE_SYMBOLS_ZERO_OR_MORE}{parameter}{self.__SPACE_SYMBOLS_ONE_OR_MORE}{value}{self.__SPACE_SYMBOLS_ZERO_OR_MORE}$"


class DaemonManagerBase:
    def __init__(self, label, action):
        self.__label = label
        self.__action = action
        self.__command_line = None
        atexit.register(self.clear_at_exit)

    def start(self):
        if self.__command_line:
            return

        self._start_impl()
        self.__command_line = str(self._build_command_line())

        Logger.instance().debug(f"[{self.__label}] {self.__action} cmd: {self.__command_line}")
        subprocess.check_call(self.__command_line, shell=True)

    def close(self):
        if not self.__command_line:
            return

        self.__find_and_kill_target_processes()
        self._close_impl()
        self.__command_line = None

    def clear_at_exit(self):
        try:
            self.close()
        except Exception as ex:
            Logger.instance().error(f"[{self.__label}] FAIL: {ex}")

    def __find_and_kill_target_processes(self):
        for process in psutil.process_iter():
            if self.__compare_cmd_line(process.cmdline()):
                Logger.instance().debug(f"[{self.__label}] KILL: {process}")
                process.kill()

    def __compare_cmd_line(self, psutil_process_cmdline):
        normalize_command_line = " ".join(shlex.split(self.__command_line))
        psutil_command_line = " ".join(psutil_process_cmdline)
        return psutil_command_line.endswith(normalize_command_line)


# https://serverfault.com/questions/723292/dnsmasq-doesnt-automatically-reload-when-entry-is-added-to-etc-hosts
# https://thekelleys.org.uk/dnsmasq/docs/dnsmasq-man.html --dhcp-hostsdir
# https://psutil.readthedocs.io/en/latest/#psutil.net_if_addrs psutil.AF_LINK (17) - получить MAC адрес сетевого интерфейса
# Сгенерировать MAC адрес
# Внимательно посмотреть на опцию --dhcp-host - она позволяет биндить mac address на hostname
# Генерируем рандомный mac адрес https://stackoverflow.com/questions/8484877/mac-address-generator-in-python
class DnsDhcpProvider(DaemonManagerBase):
    __HOST_EXTENSION = ".host"
    DNS_SUFFIX_DEFAULT = "homevpn.org"
    MY_HOST_DEFAULT = f"myhost.{DNS_SUFFIX_DEFAULT}"

    def __init__(self, interface, dhcp_host_dir="./dhcp-hostsdir", resolv_conf=ResolvConf(),
                 dns_suffix=DNS_SUFFIX_DEFAULT, my_host=MY_HOST_DEFAULT):
        super().__init__(label="DnsDhcpProvider", action="Start")
        self.__interface = interface
        self.__dhcp_host_dir = Path(dhcp_host_dir)
        self.__resolv_conf = resolv_conf
        self.__interface_ip_interface = ipaddress.IPv4Interface("192.168.0.1/24")
        self.__dns_suffix = dns_suffix
        self.__my_host = my_host

    def _start_impl(self):
        self.__make_dhcp_host_dir()
        self.__interface_ip_interface = self.__interface.get_ipv4_interface_if()
        if self.__interface_ip_interface is None:
            raise Exception("Target interface \"{}\" ipv4 address NOT ASSIGN".format(self.__interface))
        self.__add_dnsmasq_to_system_dsn_servers_list()

    def _close_impl(self):
        self.__remove_dnsmasq_from_system_dsn_servers_list()

    def add_host(self, vm_meta_data):
        TextConfigWriter(self.__get_dhcp_host_file_path(vm_meta_data)).set(
            self.__build_dhcp_host_file_content(vm_meta_data))

    def _build_command_line(self):
        return f'dnsmasq --interface={self.__interface} --bind-interfaces --dhcp-hostsdir="{self.__dhcp_host_dir}" {self.__get_dhcp_range_parameter()} --domain="{self.__dns_suffix}" --address=/{self.__my_host}/{self.__interface.get_ipv4_interface_if().ip}'

    def __make_dhcp_host_dir(self):
        self.__dhcp_host_dir.makedirs()

    def __get_dhcp_host_file_path(self, vm_meta_data):
        return os.path.join(str(self.__dhcp_host_dir), self.__get_dhcp_host_file_name(vm_meta_data.get_name()))

    def __get_dhcp_host_file_name(self, name):
        return "{}{}".format(name, self.__HOST_EXTENSION)

    @staticmethod
    def __build_dhcp_host_file_content(vm_meta_data):
        return "{},{}".format(vm_meta_data.get_mac_address_as_string(), vm_meta_data.get_name())

    def __get_dhcp_range_parameter(self):
        ip_address_start, ip_address_end = self.__get_dhcp_range()
        return "--dhcp-range={},{}".format(ip_address_start, ip_address_end)

    def __get_dhcp_range(self):
        ip_interface = self.__interface_ip_interface
        ip_address_start = ip_interface.ip + 1
        ip_address_end = list(ip_interface.network.hosts())[-1]
        if ip_address_start > ip_address_end:
            raise Exception(
                "DHCP server available ip addresses FAIL (start={}, end={}, {})".format(ip_address_start,
                                                                                        ip_address_end,
                                                                                        ip_interface))
        return ip_address_start, ip_address_end

    def __add_dnsmasq_to_system_dsn_servers_list(self):
        self.__resolv_conf.add_nameserver_if(self.__get_target_interface_ip_address())

    def __remove_dnsmasq_from_system_dsn_servers_list(self):
        self.__resolv_conf.remove_nameserver(self.__get_target_interface_ip_address())

    def __get_target_interface_ip_address(self):
        return self.__interface_ip_interface.ip


class NetworkBridge:
    def __init__(self, name, bridge_ip_address_and_mask,
                 dhcp_host_dir="./dhcp-hostsdir", internet_network_interface=None, block_internet_access=False,
                 dns_suffix=DnsDhcpProvider.DNS_SUFFIX_DEFAULT, my_host=DnsDhcpProvider.MY_HOST_DEFAULT):
        self.__interface = NetworkInterface("{}-bridge".format(name))
        self.__bridge_ip_address_and_mask = ipaddress.ip_interface(bridge_ip_address_and_mask)

        if internet_network_interface is not None:
            self.__internet_network_interface = NetworkInterface(internet_network_interface)
            Logger.instance().debug(
                f"[NetworkBridge] Internet network interface SET MANUALLY: {self.__internet_network_interface}")
        else:
            self.__internet_network_interface = None

        self.__dns_dhcp_provider = DnsDhcpProvider(self.__interface, dhcp_host_dir, dns_suffix=dns_suffix,
                                                   my_host=my_host)
        self.__block_internet_access = block_internet_access
        atexit.register(self.close)

    def create(self):
        if self.__interface.exists():
            return

        self.__set_ip_forwarding()

        try:
            subprocess.check_call("ip link add {} type bridge".format(self.__interface), shell=True)
            subprocess.check_call(
                "ip addr add {} dev {}".format(self.__get_ip_address_and_mask(), self.__interface),
                shell=True)
            subprocess.check_call("ip link set {} up".format(self.__interface), shell=True)

            self.__setup_firewall()
            self.__setup_bridge_dns_dhcp()
        except Exception as ex:
            Logger.instance().error(f"[NetworkBridge] FAIL: {ex}")
            self.close()

    def close(self):
        if not self.__interface.exists():
            return

        self.__clear_firewall()
        self.__clear_bridge_dns_dhcp()

        subprocess.check_call("ip link set {} down".format(self.__interface), shell=True)
        subprocess.check_call("ip link delete {} type bridge".format(self.__interface), shell=True)

    def add_and_configure_tap(self, tap_if, vm_meta_data):
        self.__dns_dhcp_provider.add_host(vm_meta_data)
        subprocess.check_call("ip link set {} master {}".format(tap_if, self.__interface), shell=True)

    @staticmethod
    def __set_ip_forwarding():
        subprocess.check_call("sysctl -w net.ipv4.ip_forward=1", shell=True)

    def __setup_firewall(self):
        if self.__internet_network_interface is None:
            self.__internet_network_interface = NetworkInterface.get_internet_if()
        Logger.instance().debug(f"[NetworkBridge] Internet network interface: {self.__internet_network_interface}")
        BridgeFirewall(self.__interface, self.__internet_network_interface, self.__block_internet_access).setup()

    def __clear_firewall(self):
        try:
            BridgeFirewall(self.__interface, self.__internet_network_interface,
                           self.__block_internet_access).clear_at_exit()
        except Exception as ex:
            Logger.instance().error(f"[NetworkBridge] FAIL: {ex}")

    def __setup_bridge_dns_dhcp(self):
        self.__dns_dhcp_provider.start()

    def __clear_bridge_dns_dhcp(self):
        self.__dns_dhcp_provider.close()

    def __get_ip_address_and_mask(self):
        ip_address = self.__bridge_ip_address_and_mask.ip
        ip_network = self.__bridge_ip_address_and_mask.network.prefixlen
        return "{}/{}".format(ip_address, ip_network)


class TapName:
    # название = <open_vpn_server_name>_<vm_name>_tap
    NAME_TEMPLATE = "homevpn-tap"  # fixme utopia Взять названме с конфига (open_vpn_server_name)
    # название сформировать как open_vpn_server_name + hostname VM
    # hostname VM сформировать уникально (как будем вязать на пользователя?)
    REGEX_PATTERN = r"^{}([0-9]+)".format(NAME_TEMPLATE)
    INDEX_NOT_FOUND = 1  # fixme utopia Индекс как-то криво вяжется с назначением ip адесов внутри бриджа

    def __init__(self):
        self.__index = TapName.INDEX_NOT_FOUND
        for if_name in NetworkInterface.list():
            current_index = self.get_index_from_if_name(if_name)
            if current_index > self.__index:
                self.__index = current_index
        self.__index += 1

    def __str__(self):
        return self.get_name()

    def __repr__(self):
        return self.__str__()

    def get_index(self):
        return self.__index

    def get_name(self):
        return "{}{}".format(self.NAME_TEMPLATE, self.get_index())

    @staticmethod
    def get_index_from_if_name(if_name):
        regex = re.compile(TapName.REGEX_PATTERN)
        result_raw = regex.findall(if_name)

        if len(result_raw) == 0:
            return TapName.INDEX_NOT_FOUND

        return int(result_raw[0])


class Tap:
    def __init__(self):
        self.__tap_name = TapName()
        self.__interface = NetworkInterface(self.__tap_name)

        atexit.register(self.close)

    def __str__(self):
        return str(self.__interface)

    def __repr__(self):
        return self.__str__()

    def create(self):
        if self.__interface.exists():
            return

        subprocess.check_call("ip tuntap add dev {} mode tap".format(self.__interface), shell=True)
        subprocess.check_call("ip link set {} up".format(self.__interface), shell=True)
        # ip tuntap add dev tap0 mode tap user "YOUR_USER_NAME_HERE"
        # ip link set tap0 up promisc on

    def close(self):
        if not self.__interface.exists():
            return

        subprocess.check_call("ip link set {} down".format(self.__interface), shell=True)
        subprocess.check_call("ip tuntap del dev {} mode tap".format(self.__interface), shell=True)


class Virtio:
    __WIN_DRIVERS_FILENAME = "virtio-win-drivers.iso"

    def __init__(self, project_config):
        self.__project_config = project_config

    def get_win_drivers(self):
        win_drivers_iso_path = self.__get_win_drivers_iso_path()
        if win_drivers_iso_path.exists():
            Logger.instance().debug(f"[Virtio] Win drivers was downloaded: \"{win_drivers_iso_path}\"")
            return win_drivers_iso_path

        self.__download_win_drivers(win_drivers_iso_path)
        return win_drivers_iso_path

    def __get_win_drivers_iso_path(self):
        return Path(os.path.join(self.__get_and_make_vm_dir(), Virtio.__WIN_DRIVERS_FILENAME))

    def __get_and_make_vm_dir(self):
        result = self.__project_config.get_vm_registry_dir_path()
        Path(result).makedirs()
        return result

    def __download_win_drivers(self, win_drivers_iso_path):
        virtio_win_drivers_url = self.__project_config.get_virtio_win_drivers_url()

        Logger.instance().debug(
            f"[Virtio] Win drivers DOWNLOAD: {virtio_win_drivers_url} --> \"{win_drivers_iso_path}\"")
        urllib.request.urlretrieve(virtio_win_drivers_url, str(win_drivers_iso_path))
        Logger.instance().debug(f"[Virtio] Win drivers DOWNLOAD: OK")


class UdpWatchdog:
    __IPv4_PROTO_HEADER_LENGTH_MIN = 20
    __IPv6_PROTO_HEADER_LENGTH = 40
    __UDP_PROTO_HEADER_LENGTH = 8

    __IPTABLES_RULE_MATCH = "string"
    __WAIT_TIMEOUT_AFTER_SEND_WATCHDOG_PACKET_IN_SECONDS = 2

    class ClaimCounterMismatch:
        STATE_NORMAL = 0
        STATE_CLAIM_MISMATCH = 1
        __NANOSECONDS_IN_SECOND = 10 ** 9

        def __init__(self, counter_mismatch_max,
                     counter_mismatch_claim_timeout_in_seconds):
            self.__state = self.STATE_NORMAL
            self.__expected_counter = 0
            self.__last_counter_mismatch_diff = 0
            self.__last_counter_mismatch_timestamp = None
            self.__counter_mismatch_max = counter_mismatch_max
            self.__counter_mismatch_claim_timeout_in_seconds = counter_mismatch_claim_timeout_in_seconds

        def check(self, current_counter):
            result = False
            last_counter_mismatch_diff = self.__expected_counter - current_counter
            if self.__state == self.STATE_NORMAL:
                if last_counter_mismatch_diff == 0:
                    result = True
                elif (last_counter_mismatch_diff < 0) or (last_counter_mismatch_diff > self.__counter_mismatch_max):
                    Logger.instance().warning(f"[Watchdog] Counter MISMATCH OVER: {last_counter_mismatch_diff}")
                    self.__state = self.STATE_NORMAL
                    self.__last_counter_mismatch_timestamp = None
                    self.__expected_counter = current_counter
                    result = False
                else:
                    Logger.instance().warning(
                        f"[Watchdog] Claim procedure START: current={current_counter}, expected={self.__expected_counter}, diff={last_counter_mismatch_diff}")
                    self.__state = self.STATE_CLAIM_MISMATCH
                    self.__last_counter_mismatch_timestamp = time.monotonic_ns()
                    result = True
            elif self.__state == self.STATE_CLAIM_MISMATCH:
                if last_counter_mismatch_diff == self.__last_counter_mismatch_diff:
                    if (
                            time.monotonic_ns() - self.__last_counter_mismatch_timestamp) // self.__NANOSECONDS_IN_SECOND >= self.__counter_mismatch_claim_timeout_in_seconds:
                        Logger.instance().warning(
                            f"[Watchdog] Claim procedure SUCCESS: current={current_counter}, expected={self.__expected_counter}, diff={last_counter_mismatch_diff}")
                        self.__state = self.STATE_NORMAL
                        self.__last_counter_mismatch_timestamp = None
                        self.__expected_counter = current_counter
                    result = True
                elif (last_counter_mismatch_diff < 0) or (last_counter_mismatch_diff > self.__counter_mismatch_max):
                    Logger.instance().warning(
                        f"[Watchdog] Claim procedure FAIL: current={current_counter}, expected={self.__expected_counter}, diff={last_counter_mismatch_diff}")
                    self.__state = self.STATE_NORMAL
                    self.__last_counter_mismatch_timestamp = None
                    self.__expected_counter = current_counter
                    result = False
                else:
                    Logger.instance().warning(
                        f"[Watchdog] Claim procedure RESTART: current={current_counter}, expected={self.__expected_counter}, diff={last_counter_mismatch_diff}")
                    self.__last_counter_mismatch_timestamp = time.monotonic_ns()
                    result = True

            self.__last_counter_mismatch_diff = last_counter_mismatch_diff
            return result

        def increment_expected_counter(self):
            self.__expected_counter += 1

        def get_expected_counter(self):
            return self.__expected_counter

        def set_expected_counter(self, expected_counter):
            if isinstance(expected_counter, int):
                self.__expected_counter = expected_counter
            else:
                Logger.instance().warning(f"[Watchdog] Try set expected counter FAIL: {expected_counter}")

        def get_state(self):
            return self.__state

    def __init__(self, my_external_ip_address_and_port, counter_mismatch_max=3,
                 counter_mismatch_claim_timeout_in_seconds=600):
        self.__is_init = False
        self.__secret_message = str(uuid.uuid4())
        self.__claim_counter_mismatch = UdpWatchdog.ClaimCounterMismatch(counter_mismatch_max=counter_mismatch_max,
                                                                         counter_mismatch_claim_timeout_in_seconds=counter_mismatch_claim_timeout_in_seconds)
        self.__my_external_ip_address_and_port = my_external_ip_address_and_port
        atexit.register(self.clear_at_exit)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.clear_at_exit()

    def watch(self):
        if not self.__is_init:
            self.__setup_firewall()
            self.__claim_counter_mismatch.set_expected_counter(self.__get_drop_packets_counter())
            self.__is_init = True

        try:
            self.__send_upd_packet_to_my_external_ip_address_and_port()
        except Exception as ex:
            Logger.instance().error(f"[Watchdog] Send UDP packet FAIL: {ex}")
            return False

        time.sleep(self.__WAIT_TIMEOUT_AFTER_SEND_WATCHDOG_PACKET_IN_SECONDS)
        return self.__check_drop_packets_counter()

    def clear_at_exit(self):
        try:
            if self.__is_init:
                self.__setup_firewall(clear=True)
                self.__is_init = False
        except Exception as ex:
            Logger.instance().error(f"[Watchdog] FAIL: {ex}")

    def __send_upd_packet_to_my_external_ip_address_and_port(self):
        ip_address = self.__my_external_ip_address_and_port.get_ip_address()
        udp_port = self.__my_external_ip_address_and_port.get_port()

        sock_tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_tx.sendto(self.__get_secret_message_for_send(), (str(ip_address), udp_port))
        self.__claim_counter_mismatch.increment_expected_counter()

    def __get_secret_message_for_send(self):
        return bytes(f"{self.__secret_message}/{self.__claim_counter_mismatch.get_expected_counter()}", "utf-8")

    def __check_drop_packets_counter(self):
        drop_packets_counter = self.__get_drop_packets_counter()
        if drop_packets_counter is None:
            Logger.instance().debug(
                f"[Watchdog] drop_packets_counter is null: {iptc.easy.dump_table(iptc.Table.FILTER, ipv6=False)}")
            self.__setup_firewall()
            return False

        return self.__claim_counter_mismatch.check(drop_packets_counter)

    def __setup_firewall(self, clear=False):
        # iptables -I INPUT -p udp -m string --string "testtest" --algo bm -j DROP
        table = iptc.Table(iptc.Table.FILTER)
        chain = iptc.Chain(table, "INPUT")

        rule = iptc.Rule()
        rule.protocol = "udp"

        # https://ipset.netfilter.org/iptables-extensions.man.html#lbCE
        match = iptc.Match(rule, self.__IPTABLES_RULE_MATCH)
        match.string = self.__secret_message
        match.algo = "bm"
        setattr(match, "from", str(self.__get_match_start_position()))
        match.to = str(self.__get_match_end_position())
        rule.add_match(match)

        target = iptc.Target(rule, "DROP")
        rule.target = target

        if clear:
            chain.delete_rule(rule)
        else:
            chain.insert_rule(rule)
        table.commit()
        Logger.instance().debug(
            f"[Watchdog] Table FILTER after setup {iptc.easy.dump_table(iptc.Table.FILTER, ipv6=False)}")

    def __get_match_start_position(self):
        return self.__IPv4_PROTO_HEADER_LENGTH_MIN + self.__UDP_PROTO_HEADER_LENGTH

    def __get_match_end_position(self):
        return self.__get_match_start_position() + len(self.__secret_message) + (
                self.__IPv6_PROTO_HEADER_LENGTH - self.__IPv4_PROTO_HEADER_LENGTH_MIN)

    def __get_drop_packets_counter(self):
        table = iptc.Table(iptc.Table.FILTER)
        table.refresh()
        chain = iptc.Chain(table, 'INPUT')
        for rule in chain.rules:
            for match in rule.matches:
                if (match.name == self.__IPTABLES_RULE_MATCH) and (match.string == self.__secret_message):
                    return rule.get_counters()[0]
        return None


class UnitTest_ClaimCounterMismatch(unittest.TestCase):
    def test(self):
        claim_counter_mismatch = UdpWatchdog.ClaimCounterMismatch(counter_mismatch_max=3,
                                                                  counter_mismatch_claim_timeout_in_seconds=1)

        current_counter = 0

        # Начальное состояние счётчиков
        self.assertTrue(claim_counter_mismatch.check(current_counter))
        self.assertEqual(claim_counter_mismatch.get_expected_counter(), current_counter)
        self.assertEqual(claim_counter_mismatch.get_state(), UdpWatchdog.ClaimCounterMismatch.STATE_NORMAL)

        # Первый инкремент ожидаемого и текущего счётчика
        current_counter += 1
        claim_counter_mismatch.increment_expected_counter()
        self.assertTrue(claim_counter_mismatch.check(current_counter))
        self.assertEqual(claim_counter_mismatch.get_expected_counter(), current_counter)
        self.assertEqual(claim_counter_mismatch.get_state(), UdpWatchdog.ClaimCounterMismatch.STATE_NORMAL)

        # Первое расхождение ожидаемого и текущего счётчика в плюс (т.е. разница между ожидаемым и текущим счётчиком положительная)
        # При этом разница меньше лимита counter_mismatch_max. Переходим на фазу ожидания "успокоения" текущего счётчика
        claim_counter_mismatch.increment_expected_counter()
        self.assertTrue(claim_counter_mismatch.check(current_counter))
        self.assertEqual(claim_counter_mismatch.get_expected_counter(), 2)
        self.assertEqual(claim_counter_mismatch.get_state(), UdpWatchdog.ClaimCounterMismatch.STATE_CLAIM_MISMATCH)

        # Текущий счётчик "выровнялся" с ожидаемым. По истечении counter_mismatch_claim_timeout_in_seconds если разница между ожидаемым и текущим счётчиком осталась неизменной:
        # приравниваем ожидаемый счётчик к текущему и возвращаемся к нормальной фазе
        current_counter += 1
        self.assertTrue(claim_counter_mismatch.check(current_counter))
        self.assertEqual(claim_counter_mismatch.get_expected_counter(), current_counter)
        self.assertEqual(claim_counter_mismatch.get_state(), UdpWatchdog.ClaimCounterMismatch.STATE_CLAIM_MISMATCH)
        time.sleep(1)
        self.assertTrue(claim_counter_mismatch.check(current_counter))
        self.assertEqual(claim_counter_mismatch.get_expected_counter(), current_counter)
        self.assertEqual(claim_counter_mismatch.get_state(), UdpWatchdog.ClaimCounterMismatch.STATE_NORMAL)

        # Второе расхождение ожидаемого и текущего счётчика в плюс (т.е. разница между ожидаемым и текущим счётчиком положительная)
        # При этом разница меньше лимита counter_mismatch_max. Переходим на фазу ожидания "успокоения" текущего счётчика
        claim_counter_mismatch.increment_expected_counter()
        self.assertTrue(claim_counter_mismatch.check(current_counter))
        self.assertEqual(claim_counter_mismatch.get_expected_counter(), 3)
        self.assertEqual(claim_counter_mismatch.get_state(), UdpWatchdog.ClaimCounterMismatch.STATE_CLAIM_MISMATCH)

        # До истечения counter_mismatch_claim_timeout_in_seconds считаем что проверка прошла успешно,
        # но при этом ожидаемый счётчик не приравниваем к текущему
        time.sleep(0.5)
        self.assertTrue(claim_counter_mismatch.check(current_counter))
        self.assertEqual(claim_counter_mismatch.get_expected_counter(), 3)
        self.assertEqual(claim_counter_mismatch.get_state(), UdpWatchdog.ClaimCounterMismatch.STATE_CLAIM_MISMATCH)

        # counter_mismatch_claim_timeout_in_seconds вышел и разница между ожидаемым и текущим счётчиком осталась неизменной:
        # приравниваем ожидаемый счётчик к текущему и возвращаемся к нормальной фазе
        time.sleep(1)
        self.assertTrue(claim_counter_mismatch.check(current_counter))
        self.assertEqual(claim_counter_mismatch.get_expected_counter(), current_counter)
        self.assertEqual(claim_counter_mismatch.get_state(), UdpWatchdog.ClaimCounterMismatch.STATE_NORMAL)

        # Третье расхождение ожидаемого и текущего счётчика в плюс (т.е. разница между ожидаемым и текущим счётчиком положительная)
        # При этом разница меньше лимита counter_mismatch_max. Переходим на фазу ожидания "успокоения" текущего счётчика
        claim_counter_mismatch.increment_expected_counter()
        self.assertTrue(claim_counter_mismatch.check(current_counter))
        self.assertEqual(claim_counter_mismatch.get_expected_counter(), 3)
        self.assertEqual(claim_counter_mismatch.get_state(), UdpWatchdog.ClaimCounterMismatch.STATE_CLAIM_MISMATCH)

        # До истечения counter_mismatch_claim_timeout_in_seconds считаем что проверка прошла успешно,
        # но при этом ожидаемый счётчик не приравниваем к текущему
        time.sleep(0.5)
        self.assertTrue(claim_counter_mismatch.check(current_counter))
        self.assertEqual(claim_counter_mismatch.get_expected_counter(), 3)
        self.assertEqual(claim_counter_mismatch.get_state(), UdpWatchdog.ClaimCounterMismatch.STATE_CLAIM_MISMATCH)

        # Ожидаемый счётчик инкрементировался три раза. Мы вышли за лимит counter_mismatch_max.
        # Поэтому ожидание "успокоения" провалилось, приравниваем ожидаемый счётчик к текущему и возвращаемся к нормальной фазе
        claim_counter_mismatch.increment_expected_counter()
        claim_counter_mismatch.increment_expected_counter()
        claim_counter_mismatch.increment_expected_counter()
        self.assertEqual(claim_counter_mismatch.get_expected_counter(), 6)
        self.assertFalse(claim_counter_mismatch.check(current_counter))
        self.assertEqual(claim_counter_mismatch.get_expected_counter(), current_counter)
        self.assertEqual(claim_counter_mismatch.get_state(), UdpWatchdog.ClaimCounterMismatch.STATE_NORMAL)

        # Расхождение ожидаемого и текущего счётчика в минус (т.е. разница между ожидаемым и текущим счётчиком отрицательная)
        # Это аномалия, приравниваем ожидаемый счётчик к текущему и возвращаемся к нормальной фазе
        current_counter = 100
        self.assertFalse(claim_counter_mismatch.check(current_counter))
        self.assertEqual(claim_counter_mismatch.get_expected_counter(), current_counter)
        self.assertEqual(claim_counter_mismatch.get_state(), UdpWatchdog.ClaimCounterMismatch.STATE_NORMAL)


# fixme utopia Необходимо проверять параметры загрузки linux kernel (см. /proc/cmdline)
# Нам нужен парсер командной строки для linux kernel
class Iommu:
    # fixme utopia Вырубить виртуализацию в биос и проверить появится ли
    __IOMMU_SYS_FS_PATH = "/sys/class/iommu/"

    # проверить что в /etc/default/grub есть intel_iommu=on iommu=pt и в dmesg есть
    # iommu: Default domain type: Passthrough
    def check(self):
        return os.path.exists(self.__IOMMU_SYS_FS_PATH) and os.path.isdir(self.__IOMMU_SYS_FS_PATH)

    def is_intel(self):
        return self.check() and self.__is_cpu_vendor("intel")

    def is_amd(self):
        return self.check() and self.__is_cpu_vendor("amd")

    def is_arm(self):
        return self.check() and self.__is_cpu_vendor("arm")

    # https://docs.kernel.org/admin-guide/kernel-parameters.html
    def get_kernel_parameters(self):
        if self.is_intel():
            return [{"intel_iommu": "on", "iommu": "pt"}]
        elif self.is_amd():
            return [{"amd_iommu": "on", "iommu": "pt"}]
        return []

    def __is_cpu_vendor(self, cpu_vendor):
        try:
            return str(cpu_vendor) in str(cpuinfo.get_cpu_info()['vendor_id_raw']).lower()
        except Exception:
            return False


# https://pcisig.com/sites/default/files/files/PCI_Code-ID_r_1_11__v24_Jan_2019.pdf
class PciClassCode(UInt16Hex):
    BASE_CLASS_BACKWARD_COMPATIBILITY = 0x00
    BASE_CLASS_BACKWARD_COMPATIBILITY_ALL_EXCEPT_VGA = 0x00
    BASE_CLASS_BACKWARD_COMPATIBILITY_VGA = 0x01
    BASE_CLASS_VGA = 0x03

    BASE_CLASS_BRIDGE_DEVICE = 0x06
    BASE_CLASS_BRIDGE_DEVICE_HOST = 0x00
    BASE_CLASS_BRIDGE_DEVICE_ISA = 0x01
    BASE_CLASS_BRIDGE_DEVICE_EISA = 0x02
    BASE_CLASS_BRIDGE_DEVICE_MCA = 0x03
    BASE_CLASS_BRIDGE_DEVICE_PCI_TO_PCI = 0x04
    BASE_CLASS_BRIDGE_DEVICE_PCMCIA = 0x05
    BASE_CLASS_BRIDGE_DEVICE_NU_BUS = 0x06
    BASE_CLASS_BRIDGE_DEVICE_CARD_BUS = 0x07
    BASE_CLASS_BRIDGE_DEVICE_RACE_WAY = 0x08
    BASE_CLASS_BRIDGE_DEVICE_SEMI_TRANSPARENT_PCI_TO_PCI = 0x09
    BASE_CLASS_BRIDGE_DEVICE_INFINIBAND_TO_PCI = 0x0A

    BASE_CLASS_SERIAL_BUS_CONTROLLER = 0x0C
    BASE_CLASS_SERIAL_BUS_CONTROLLER_USB = 0x03
    BASE_CLASS_SERIAL_BUS_CONTROLLER_USB_UHCI = 0x00
    BASE_CLASS_SERIAL_BUS_CONTROLLER_USB_OHCI = 0x10
    BASE_CLASS_SERIAL_BUS_CONTROLLER_USB_EHCI = 0x20
    BASE_CLASS_SERIAL_BUS_CONTROLLER_USB_XHCI = 0x30
    BASE_CLASS_SERIAL_BUS_CONTROLLER_USB_WITHOUT_SPECIFIC_PROG_IF = 0x80
    BASE_CLASS_SERIAL_BUS_CONTROLLER_USB_DEVICE = 0xFE

    BASE_CLASS_SERIAL_BUS_CONTROLLER_SMBUS = 0x05

    def __new__(cls, class_code=0):
        return super(PciClassCode, cls).__new__(cls, class_code)

    def get_base_class(self):
        return (self.__int__() >> BitUtils.BITS_IN_BYTE) & BitUtils.LSB_TETRAD_MASK

    def get_sub_class(self):
        return self.__int__() & BitUtils.LSB_TETRAD_MASK

    # https://github.com/xiaoran007/pypci/blob/v0.0.4/src/pypci/backend/pci.py#L74
    def is_vga(self):
        return self.get_base_class() == self.BASE_CLASS_VGA or (
                self.get_base_class() == self.BASE_CLASS_BACKWARD_COMPATIBILITY and self.get_sub_class() == self.BASE_CLASS_BACKWARD_COMPATIBILITY_VGA)

    def is_usb_host_controller(self, prog_if):
        return self.is_usb_uhci_controller(prog_if) or self.is_usb_ohci_controller(
            prog_if) or self.is_usb_ehci_controller(prog_if) or self.is_usb_xhci_controller(prog_if)

    def is_usb_uhci_controller(self, prog_if):
        return self.is_usb() and (
                prog_if == self.BASE_CLASS_SERIAL_BUS_CONTROLLER_USB_UHCI)

    def is_usb_ohci_controller(self, prog_if):
        return self.is_usb() and (
                prog_if == self.BASE_CLASS_SERIAL_BUS_CONTROLLER_USB_OHCI)

    def is_usb_ehci_controller(self, prog_if):
        return self.is_usb() and (
                prog_if == self.BASE_CLASS_SERIAL_BUS_CONTROLLER_USB_EHCI)

    def is_usb_xhci_controller(self, prog_if):
        return self.is_usb() and (
                prog_if == self.BASE_CLASS_SERIAL_BUS_CONTROLLER_USB_XHCI)

    def is_usb(self):
        return self.get_base_class() == self.BASE_CLASS_SERIAL_BUS_CONTROLLER and self.get_sub_class() == self.BASE_CLASS_SERIAL_BUS_CONTROLLER_USB

    def is_isa_bridge(self):
        return self.get_base_class() == self.BASE_CLASS_BRIDGE_DEVICE and self.get_sub_class() == self.BASE_CLASS_BRIDGE_DEVICE_ISA


# https://github.com/pciutils/pciutils/blob/master/pci.ids
class PciVendorId(UInt16Hex):
    INTEL = 0x8086

    def __new__(cls, vendor_id=0):
        return super(PciVendorId, cls).__new__(cls, vendor_id)

    def is_intel(self):
        return self.__int__() == self.INTEL


def get_all_subclasses(cls):
    result = cls.__subclasses__().copy()
    for sub_cls in cls.__subclasses__():
        for sub_sub_cls in get_all_subclasses(sub_cls):
            if not sub_sub_cls in result:
                result.append(sub_sub_cls)
    result.reverse()
    return result


class UnitTest_get_all_subclasses(unittest.TestCase):
    class Foo(object): pass

    class Bar(Foo): pass

    class Baz(Foo): pass

    class Bing(Bar): pass

    def test(self):
        subclass_name_list = []
        for sub_cls in get_all_subclasses(UnitTest_get_all_subclasses.Foo):
            subclass_name_list.append(sub_cls.__name__)

        self.assertEqual(subclass_name_list, ["Bing", "Baz", "Bar"])


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
        if id(self) == id(other):
            return True
        return self.__str__() == other.__str__()

    def get_address_without_domain(self):
        return f"{self.bus}:{self.slot}.{self.func}"

    @staticmethod
    def get_regex(is_capture=False, is_start_end_of_line=False):
        tmp = PciAddress()
        result = ""
        if is_start_end_of_line:
            result += "^"
        result += f"(?>{tmp.get_regex_for(PciAddress.__DOMAIN, is_capture)}:)?"
        result += f"{tmp.get_regex_for(PciAddress.__BUS, is_capture)}:"
        result += f"{tmp.get_regex_for(PciAddress.__SLOT, is_capture)}\."
        result += f"{tmp.get_regex_for(PciAddress.__FUNC, is_capture)}"
        if is_start_end_of_line:
            result += "$"
        return result


class UnitTest_PciAddress(unittest.TestCase):
    class PciAddressTest(PciAddress):
        pass

    class UnknownClass:
        pass

    def test(self):
        ref_table = [
            (PciAddress, "",
             {"is_exception": True}),
            (PciAddress, "Hello world",
             {"is_exception": True}),
            (PciAddress, 17,
             {"is_exception": True}),
            (PciAddress, UnitTest_PciAddress.UnknownClass,
             {"is_exception": True}),
            (PciAddress, "0000:00:00.0",
             {"expected": "0000:00:00.0", "is_exception": False,
              "expected_dict": {"domain": 0, "bus": 0, "slot": 0, "func": 0}}),
            (PciAddress, "0000:00:02.0",
             {"expected": "0000:00:02.0", "is_exception": False,
              "expected_dict": {"domain": 0, "bus": 0, "slot": 2, "func": 0}}),
            (PciAddress, "0000:00:1F.1",
             {"expected": "0000:00:1f.1", "is_exception": False,
              "expected_dict": {"domain": 0, "bus": 0, "slot": 0x1F, "func": 1}}),
            (PciAddress, "00:1F.1",
             {"expected": f"{PciAddress.DOMAIN_DEFAULT}:00:1f.1", "is_exception": False,
              "expected_dict": {"domain": 0, "bus": 0, "slot": 0x1F, "func": 1}}),
            (PciAddress, None,
             {"expected": f"{PciAddress.DOMAIN_DEFAULT}:00:00.0", "is_exception": False,
              "expected_dict": {"domain": 0, "bus": 0, "slot": 0, "func": 0}}),
            (PciAddress, {"bus": 1, "slot": 2, "func": 3},
             {"expected": f"{PciAddress.DOMAIN_DEFAULT}:01:02.3", "is_exception": False,
              "expected_dict": {"domain": 0, "bus": 1, "slot": 2, "func": 3}}),
            (PciAddress, {"bus0": 1, "slot": 0xFF, "func_": 3},
             {"expected": f"{PciAddress.DOMAIN_DEFAULT}:00:ff.0", "is_exception": False,
              "expected_dict": {"domain": 0, "bus": 0, "slot": 0xFF, "func": 0}}),
            (PciAddress, {},
             {"expected": f"{PciAddress.DOMAIN_DEFAULT}:00:00.0", "is_exception": False,
              "expected_dict": {"domain": 0, "bus": 0, "slot": 0, "func": 0}}),
            (PciAddress, PciAddress(),
             {"expected": f"{PciAddress.DOMAIN_DEFAULT}:00:00.0", "is_exception": False,
              "expected_dict": {"domain": 0, "bus": 0, "slot": 0, "func": 0}}),
            (PciAddress, PciAddress("AA:BB.255"),
             {"expected": f"{PciAddress.DOMAIN_DEFAULT}:aa:bb.255", "is_exception": False,
              "expected_dict": {"domain": 0, "bus": 0xAA, "slot": 0xBB, "func": 255}}),
            (PciAddress, UnitTest_PciAddress.PciAddressTest("AA:BB.255"),
             {"expected": f"{PciAddress.DOMAIN_DEFAULT}:aa:bb.255", "is_exception": False,
              "expected_dict": {"domain": 0, "bus": 0xAA, "slot": 0xBB, "func": 255}}),
            (UnitTest_PciAddress.PciAddressTest, PciAddress("AA:BB.255"),
             {"expected": f"{PciAddress.DOMAIN_DEFAULT}:aa:bb.255", "is_exception": False,
              "expected_dict": {"domain": 0, "bus": 0xAA, "slot": 0xBB, "func": 255}}),
        ]

        for pci_address_type, initiate, test_data in ref_table:
            pci_address = None
            try:
                pci_address = pci_address_type(initiate)
                self.assertFalse(test_data["is_exception"], f"No exception for \"{initiate}\"")
            except Exception as ex:
                self.assertTrue(test_data["is_exception"], f"Exception for \"{initiate}\": {ex}")

            if pci_address is not None:
                self.assertEqual(pci_address.get_fields_as_dict(), test_data["expected_dict"])
                self.assertEqual(str(pci_address_type(initiate)), test_data["expected"])


# https://en.wikipedia.org/wiki/PCI_configuration_space
class Pci(BaseParser):
    # https://github.com/pciutils/pciutils/blob/master/ls-caps.c#L1457
    class PciExpressCapability(int):
        def __new__(cls, value=0):
            return super(Pci.PciExpressCapability, cls).__new__(cls, int(bool(value)))

        @staticmethod
        def get_regex():
            return "Capabilities: \[[0-9A-Fa-f]{2}\] Express"

    # https://github.com/pciutils/pciutils/blob/master/ls-ecaps.c#L266
    class AcsCapability(int):
        def __new__(cls, value=0):
            return super(Pci.AcsCapability, cls).__new__(cls, int(bool(value)))

        @staticmethod
        def get_regex():
            return "Capabilities: \[[0-9A-Fa-f]{3} v\d+\] Access Control Services"

    # https://github.com/pciutils/pciutils/blob/master/ls-ecaps.c#L381
    class SriovCapability(int):
        def __new__(cls, value=0):
            return super(Pci.SriovCapability, cls).__new__(cls, int(bool(value)))

        @staticmethod
        def get_regex():
            return "Capabilities: \[[0-9A-Fa-f]{3} v\d+\] Single Root I/O Virtualization \(SR-IOV\)"

    __ADDRESS = "address"
    __CLASS_NAME = "class_name"
    __CLASS_CODE = "class_code"
    __DEVICE_NAME = "device_name"
    __VENDOR_ID = "vendor_id"
    __DEVICE_ID = "device_id"
    __REVISION = "revision"
    __PROG_IF = "prog_if"
    __SUBSYSTEM_NAME = "subsystem_name"
    __SUBSYSTEM_VENDOR_ID = "subsystem_vendor_id"
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
               __VENDOR_ID: {"type": PciVendorId},
               __DEVICE_ID: {"type": UInt16Hex},
               __REVISION: {"type": UInt8Hex},
               __PROG_IF: {"type": UInt8Hex},
               __SUBSYSTEM_NAME: {"type": String},
               __SUBSYSTEM_VENDOR_ID: {"type": PciVendorId},
               __SUBSYSTEM_ID: {"type": UInt16Hex},
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

    def get_id(self):
        return f"{self.vendor_id}:{self.device_id}"

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

    def get_parent_address_list(self):
        return self.__get_related_address_list("supplier")

    def get_child_address_list(self):
        return self.__get_related_address_list("consumer")

    def __get_related_address_list(self, name):
        if not CurrentOs.is_linux():
            return []

        result = list()
        for path in pathlib.Path(self.__get_sysfs_pci_device_path()).glob(f"{name}:pci:*"):
            try:
                result.append(PciAddress(str(path.name)))
            except Exception as ex:
                pass
        return result

    # https://www.intel.com/content/www/us/en/docs/graphics-for-linux/developer-reference/1-0/dump-video-bios.html
    # https://stackoverflow.com/a/52174005
    def get_rom(self, dir_path_for_save_rom_file):
        rom_file_path = Path(self.__get_sysfs_pci_device_path()).join("rom")
        if not rom_file_path.file_exists():
            Logger.instance().warning(f"[PCI/{self.address}] ROM NOT FOUND: {rom_file_path}")
            return None

        with open(rom_file_path.get(), "tw") as f:
            f.write("1")

        dir_path_for_save_rom_file.mkdir(parents=True, exist_ok=True)
        result = Path(dir_path_for_save_rom_file / self.get_rom_file_name())
        result.copy_from(rom_file_path)

        with open(rom_file_path.get(), "tw") as f:
            f.write("0")

        return result

    def get_rom_file_name(self):
        return f"{self.address}_{self.get_id()}_rom.bin"

    def __get_sysfs_pci_device_path(self):
        return f"/sys/bus/pci/devices/{self.address}"

    def is_pci_express(self):
        return self.is_capabilities(is_pci_express=True)

    def is_capabilities(self, is_pci_express=None, is_acs=None, is_sriov=None):
        table = {self.__IS_PCI_EXPRESS: is_pci_express, self.__IS_ACS: is_acs, self.__IS_SRIOV: is_sriov}

        for key, value in table.items():
            if value is not None:
                if bool(value) != bool(self[key]):
                    return False
        return True

    class PciList(list):

        def __str__(self):
            return json.dumps(self, default=lambda o: o.get_fields_as_dict())

        def __repr__(self):
            return self.__str__()

        @staticmethod
        def from_string(model):
            return Pci.PciList.from_json(json.loads(model))

        @staticmethod
        def from_json(model):
            result = Pci.PciList()
            for item in model:
                result.append(Pci.from_json(item))
            return result

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
                    result[pci.iommu_group].append(pci)
                else:
                    result[pci.iommu_group] = Pci.PciList([pci])
            return result

        def get_pci_list_by_iommu_group(self, iommu_group):
            pci_table_by_iommu_group = self.get_pci_table_by_iommu_group()
            if iommu_group in pci_table_by_iommu_group:
                return pci_table_by_iommu_group[iommu_group]
            return Pci.PciList()

        def get_vga_list(self, with_consumer=False):
            result = Pci.PciList()
            for pci in self:
                if pci.class_code.is_vga():
                    result.append(pci)
                    if with_consumer:
                        result.extend(self.get_by_address(pci.get_child_address_list()))
            return result

        def get_usb_host_list(self):
            result = Pci.PciList()
            for pci in self:
                if pci.class_code.is_usb_host_controller(pci.prog_if):
                    result.append(pci)
            return result

        def get_isa_bridge_list(self):
            result = Pci.PciList()
            for pci in self:
                if pci.class_code.is_isa_bridge():
                    result.append(pci)
            return result

        def get_pci_list_by_capabilities(self, is_pci_express=None, is_acs=None, is_sriov=None):
            result = Pci.PciList()
            for pci in self:
                if pci.is_capabilities(is_pci_express=is_pci_express, is_acs=is_acs, is_sriov=is_sriov):
                    result.append(pci)
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
                    if len(pci_table_by_iommu_group[iommu_group]) != len(pci_list):
                        if len(pci_list.get_pci_list_by_capabilities(is_pci_express=True, is_acs=False)) != len(
                                pci_list):
                            # Условия для применения ACS override patch: PCI Express устройство (is_pci_express=True) и отсутствие capability ACS (is_acs=False)
                            # https://github.com/benbaker76/linux-acs-override/blob/main/6.3/acso.patch#L101
                            result = None
                            pci_list_problematic = "\n".join(
                                [f"    [{pci.get_id()}|{pci.address}] ({pci.class_name}) {pci.device_name}" for pci in
                                 pci_list])
                            Logger.instance().warning(
                                f"ACS override patch not applicable for PCI devices in IOMMU group {iommu_group}:\n{pci_list_problematic}")
                        else:
                            if result is not None:
                                result = False
            return result

        def get_by_address(self, pci_address_list):
            result = Pci.PciList()
            for pci in self:
                if pci.address in pci_address_list:
                    result.append(pci)
            return result

        def get_pci_id_list(self):
            return [pci.get_id() for pci in self]

        ## Заблокировать ли прочие VGA для данной виртуальной машины
        # @details Требуется для обеспечения проброса Intel integrated GPU (IGD, Integrated Graphics Device) в так называемом legacy режиме, подробно https://gitlab.com/qemu-project/qemu/-/blob/master/docs/igd-assign.txt?ref_type=heads
        # @return true - заблокировать прочие VGA для данной виртуальной машины; false - можно использовать множественные VGA, в том числе виртуальные VGA
        def is_other_vga_disable(self):
            for pci in self:
                if pci.is_other_vga_disable():
                    return True
            return False

        ## Проверить пригодность платформы (чипсета) для данной виртуальной машины
        # @details Некоторые сочетания Host BIOS/UEFI / Guest BIOS/UEFI не совместимы с пробросом PCI устройств
        # @details Если платформа (чипсет) не подходят метод бросит исключение с описанием проблемы
        # @param [in] qemu_platform Платформа (чипсет) виртуальной машины
        def check_platform(self, qemu_platform):
            for pci in self:
                pci.check_platform(qemu_platform)

    @staticmethod
    def get_list():
        result = Pci.PciList()

        lspci_out = Pci.__run_lspci()

        for match in re.finditer(Pci.__get_regex(), lspci_out, flags=re.MULTILINE):
            for key, value in match.groupdict().items():
                if value is not None:
                    if key == Pci.__ADDRESS:
                        result.append(Pci())

                    pci = result[-1]
                    pci[key] = value

        for index, pci in enumerate(result):
            result[index] = Pci.__build(pci)
        return result

    @staticmethod
    def __get_regex():
        tmp = Pci()
        result = ""
        result += f"{tmp.get_regex_for(Pci.__ADDRESS)} "
        result += f"{tmp.get_regex_for(Pci.__CLASS_NAME)} "
        result += f"\[{tmp.get_regex_for(Pci.__CLASS_CODE)}]: "
        result += f"{tmp.get_regex_for(Pci.__DEVICE_NAME)} "
        result += f"\[{tmp.get_regex_for(Pci.__VENDOR_ID)}:{tmp.get_regex_for(Pci.__DEVICE_ID)}\] "
        result += f"\(rev {tmp.get_regex_for(Pci.__REVISION)}\)"
        result += f"(?> \(prog-if {tmp.get_regex_for(Pci.__PROG_IF)} \[.*\]\))?"
        result += "|"
        result += f"Subsystem: {tmp.get_regex_for(Pci.__SUBSYSTEM_NAME)} "
        result += f"\[{tmp.get_regex_for(Pci.__SUBSYSTEM_VENDOR_ID)}:{tmp.get_regex_for(Pci.__SUBSYSTEM_ID)}\]"
        result += "|"
        result += f"IOMMU group: {tmp.get_regex_for(Pci.__IOMMU_GROUP)}"
        result += "|"
        result += f"Kernel driver in use: {tmp.get_regex_for(Pci.__KERNEL_MODULE)}"
        result += "|"
        result += f"{tmp.get_regex_for(Pci.__IS_PCI_EXPRESS)}"
        result += "|"
        result += f"{tmp.get_regex_for(Pci.__IS_ACS)}"
        result += "|"
        result += f"{tmp.get_regex_for(Pci.__IS_SRIOV)}"
        return result

    @staticmethod
    def __build(base_pci):
        for sub_cls in get_all_subclasses(Pci):
            if sub_cls.is_my_instance(base_pci):
                return sub_cls(base_pci)
        return base_pci

    @staticmethod
    def __run_lspci():
        cmd_result = subprocess.run(Pci.__CMD_LINE, shell=True, capture_output=True, text=True)
        if cmd_result.returncode:
            return ""
        return cmd_result.stdout


class VfioPci:
    def __init__(self, pci_list):
        self.__pci_list = pci_list
        if not isinstance(self.__pci_list, Pci.PciList):
            raise Exception(f"[VfioPci] pci_list TYPE MISMATCH: {type(self.__pci_list)}")

    def __str__(self):
        return str(self.__pci_list)

    def __repr__(self):
        return self.__str__()

    @staticmethod
    def from_string(model):
        return VfioPci(Pci.PciList.from_string(model))

    @staticmethod
    def from_json(model):
        return VfioPci(Pci.PciList.from_json(model))

    def get_pci_list(self):
        return self.__pci_list

    def get_pci_id_list(self):
        return self.__pci_list.get_pci_id_list()

    @staticmethod
    def get_device_for_passthrough(pci, vm_meta_data):
        # PCI устройство нельзя пробросить если оно не включено в iommu группу
        if pci.iommu_group is None:
            return {}

        vfio_pci_options_table = {"host": pci.address}
        vfio_pci_options_table.update(pci.get_vfio_pci_options_table(vm_meta_data))
        return {"-device": {"vfio-pci": vfio_pci_options_table}}

    def get_kernel_parameters(self):
        if len(self.__pci_list) == 0:
            return []

        result = [{"vfio_pci.ids": self.get_pci_id_list()}]

        for pci in self.__pci_list:
            result.extend(pci.get_kernel_parameters())
        return result

    def get_qemu_parameters(self, vm_meta_data):
        result = []
        for pci in self.__pci_list:
            result.extend(pci.get_qemu_parameters(vm_meta_data))
        return result

    def is_other_vga_disable(self):
        return self.__pci_list.is_other_vga_disable()

    def check_platform(self, qemu_platform):
        return self.__pci_list.check_platform(qemu_platform)


# https://docs.kernel.org/driver-api/vfio-mediated-device.html
# https://docs.kernel.org/driver-api/vfio.html
class Vfio:
    def __init__(self, vfio_pci, iommu=Iommu(), is_acs_override=True):
        self.__vfio_pci = vfio_pci
        self.__iommu = iommu
        self.__is_acs_override = bool(is_acs_override)

    def get_kernel_parameters(self):
        result = [{"modules_load": ["vfio", "vfio_pci", "vfio_iommu_type1", "vfio_virqfd"], "kvm.ignore_msrs": "1",
                   "vfio_io_iommu_type1.allow_unsafe_interrupts": "1"}]
        result.extend(self.__vfio_pci.get_kernel_parameters())
        result.extend(self.__iommu.get_kernel_parameters())
        pci_id_list = self.__vfio_pci.get_pci_id_list()
        if self.__is_acs_override and len(pci_id_list) > 0:
            result.append({"pcie_acs_override": [{"id": pci_id_list}]})
        return result


class QemuCdRom:
    OS_DISTR_INDEX = 0
    VIRTIO_WIN_DRIVERS_INDEX = 1
    HW_CDROM_INDEX = 2

    def __init__(self, os_distr_path=None, virtio_win_drivers_path=None, hw_cdrom_path=Path("/dev/sr0")):
        self.__table = {self.OS_DISTR_INDEX: os_distr_path,
                        self.VIRTIO_WIN_DRIVERS_INDEX: virtio_win_drivers_path,
                        self.HW_CDROM_INDEX: hw_cdrom_path}

    def get_qemu_parameters(self):
        result = []
        for index, path in self.__table.items():
            qemu_parameters_item = self.__get_qemu_parameters_template(index, path)
            if qemu_parameters_item is not None:
                result.append(qemu_parameters_item)
        return result

    def __get_qemu_parameters_template(self, index, path):
        if path is None:
            return None

        if not Path(path).exists():
            return None

        return {"-drive": {"file": str(path), "media": "cdrom", "if": "ide", "index": index}}


# https://forum.proxmox.com/threads/laptop-keyboard-touchpad-passthough-to-a-vm.135399/
# qemu-system-$(uname -m) -object input-linux,help
# Тачпад ведёт себя не адекватно поэтому не пробрасываем его
class QemuBuiltinKeyboardAndMousePassthrough:
    INPUT_DEV_PATH = "/dev/input/by-path"

    def __init__(self):
        self.__table = {"kbd": {"grab_all": "on", "repeat": "on"}}  # "mouse": {},

    def get_qemu_parameters(self):
        result = []
        for target, additional_args in self.__table.items():
            result.extend(self.__get_qemu_parameters(target, additional_args))
        return result

    def __get_qemu_parameters(self, target, additional_args):
        result = []
        index = 0
        for path in pathlib.Path(self.INPUT_DEV_PATH).glob(f"platform-*-event-{target}"):
            args = {"id": f"{target}{index}", "evdev": path}
            args.update(additional_args)
            result.append({"-object": {"input-linux": args}})
            index = index + 1
        return result


# Пока не доступно
# https://gitlab.com/qemu-project/qemu/-/issues/242
# https://github.com/utmapp/UTM/issues/5455
# https://wiki.archlinux.org/title/PCI_passthrough_via_OVMF#%22Error_43:_Driver_failed_to_load%22_with_mobile_(Optimus/max-q)_nvidia_GPUs
# https://www.wensley.org.uk/ioacpi
# https://www.wensley.org.uk/c/ioacpi.c
class QemuBattery:
    pass


class QemuPlatform:
    QEMU_PLATFORM_I440FX_BIOS = "i440fx+bios"
    QEMU_PLATFORM_Q35_BIOS = "q35+bios"
    QEMU_PLATFORM_Q35_UEFI = "q35+uefi"
    QEMU_PLATFORM_Q35_UEFI_SECURE = "q35+uefi-secure"

    QEMU_PLATFORM_LIST = [QEMU_PLATFORM_I440FX_BIOS, QEMU_PLATFORM_Q35_BIOS, QEMU_PLATFORM_Q35_UEFI,
                          QEMU_PLATFORM_Q35_UEFI_SECURE]

    def __init__(self, vm_meta_data, vm_platform=QEMU_PLATFORM_I440FX_BIOS):
        self.__vm_meta_data = vm_meta_data
        self.__vm_platform = vm_platform
        self.__tpm = None
        if self.is_secure_boot():
            self.__tpm = TpmEmulator(self.__vm_meta_data)

    def before_start_vm(self):
        if self.__tpm is None:
            return
        self.__tpm.start()

    def after_stop_vm(self):
        if self.__tpm is None:
            return
        self.__tpm.close()

    def get_qemu_parameters(self):
        qemu_bios = QemuBios(self.__vm_meta_data)
        if self.__vm_platform == self.QEMU_PLATFORM_Q35_BIOS:
            qemu_bios = QemuBios("q35")
        elif self.__vm_platform == self.QEMU_PLATFORM_Q35_UEFI:
            qemu_bios = QemuUefi(self.__vm_meta_data, is_secure_boot=False)
        elif self.__vm_platform == self.QEMU_PLATFORM_Q35_UEFI_SECURE:
            qemu_bios = QemuUefi(self.__vm_meta_data, is_secure_boot=True)

        result = qemu_bios.get_qemu_parameters()
        if self.__tpm is not None:
            result.extend(self.__tpm.get_qemu_parameters())
        return result

    def is_bios_boot(self):
        return self.is_i440fx_bios_boot() or self.__vm_platform in self.get_bios_boot_platform_list()

    def is_i440fx_bios_boot(self):
        return self.__vm_platform is None or self.__vm_platform in self.get_i440fx_bios_boot_platform_list()

    def is_uefi_boot(self):
        return self.__vm_platform is not None and (self.__vm_platform in self.get_uefi_boot_platform_list())

    def is_secure_boot(self):
        return self.__vm_platform is not None and (self.__vm_platform in self.get_secure_boot_platform_list())

    def get_bios_boot_platform_list(self):
        return [self.QEMU_PLATFORM_I440FX_BIOS, self.QEMU_PLATFORM_Q35_BIOS]

    def get_i440fx_bios_boot_platform_list(self):
        return [self.QEMU_PLATFORM_I440FX_BIOS]

    def get_uefi_boot_platform_list(self):
        return [self.QEMU_PLATFORM_Q35_UEFI, self.QEMU_PLATFORM_Q35_UEFI_SECURE]

    def get_secure_boot_platform_list(self):
        return [self.QEMU_PLATFORM_Q35_UEFI_SECURE]


class VgaPciIntel(Pci):
    def __init__(self, pci):
        super().__init__()
        self._init(pci)
        self.__cpu = Cpu.get_cpu0()

    # https://pve.proxmox.com/wiki/PCI_Passthrough#%22BAR_3:_can't_reserve_[mem]%22_error
    def get_kernel_parameters(self):
        result = super().get_kernel_parameters()
        result.extend([{"module_blacklist": ["snd_hda_intel", "snd_hda_codec_hdmi"]},
                       {"video": {"efifb": "off", "vesafb": "off", "vesa": "off", "simplefb": "off"}},
                       {"l1tf": ["full", "force"]},
                       {"initcall_blacklist": "sysfb_init"}])
        return result

    # https://github.com/qemu/qemu/blob/master/docs/igd-assign.txt
    # https://www.reddit.com/r/VFIO/comments/i9dbyp/this_is_how_i_managed_to_passthrough_my_igd/
    # fixme utopia Проброс с OVMF + __VGA_PASSTHROUGH_MODE_UPT
    def get_vfio_pci_options_table(self, vm_meta_data):
        result = super().get_vfio_pci_options_table(vm_meta_data)

        if self.__check_passthrough_in_legacy_mode():
            result.update({"x-igd-gms": "9", "addr": "0x02", "rombar": 0, "x-vga": "on", "x-igd-opregion": "on"})

            rom_file_path = self.get_rom(vm_meta_data.get_working_dir_path())
            if rom_file_path is not None:
                result["romfile"] = rom_file_path

        else:
            result.update({"x-vga": "on", "x-igd-opregion": "on"})

        return result

    def get_qemu_parameters(self, vm_meta_data):
        result = super().get_qemu_parameters(vm_meta_data)
        if len(result) > 0 and self.is_other_vga_disable():
            result.append({"-vga": "none"})
            # result.append({"-fw_cfg": {"name": "opt/igd-opregion", "file": "/home/utopia/HomeVpn/opregion.bin"}})
            # result.append({"-fw_cfg": {"name": "opt/igd-bdsm-size", "file": "/home/utopia/HomeVpn/bdsmSize.bin"}})
            # result.append({"-machine": "pc-i440fx-2.2"})
            # result.append({"-device": { "vfio-pci-igd-lpc-bridge": { "addr": "0x1f" } }})
        return result

    def is_other_vga_disable(self):
        return self.__check_passthrough_in_legacy_mode()

    def check_platform(self, qemu_platform):
        if self.__check_passthrough_in_legacy_mode():
            if CurrentOs.is_bios_boot() and qemu_platform.is_i440fx_bios_boot():
                return

            recommendation = list()
            if not qemu_platform.is_i440fx_bios_boot():
                recommendation.append(f"use {qemu_platform.QEMU_PLATFORM_I440FX_BIOS}")
            if not CurrentOs.is_bios_boot():
                recommendation.append("OS must be boot in BIOS mode")
            raise Exception(
                f"[VgaPciIntel] Current platform NOT SUPPORTED for igd passthrough: {', '.join(recommendation)}")
        else:
            if CurrentOs.is_bios_boot() and qemu_platform.is_bios_boot():
                return
            if CurrentOs.is_uefi_boot() and qemu_platform.is_uefi_boot():  # fixme utopia Проверить на Ноутбуке Галины
                # https://lore.kernel.org/all/20250312102929.329ff4f5.alex.williamson@redhat.com/T/
                # https://gitlab.com/qemu-project/qemu/-/issues/1538
                # Так в UPT режиме работать будет?
                return
            # fixme utopia Перепроверить с OVMF отсюда. Будет ли работать комбинация BIOS Host / UEFI Guest
            # https://github.com/x78x79x82x79/i915ovmfPkg
            # https://github.com/patmagauran/i915ovmfPkg

            if CurrentOs.is_bios_boot():
                raise Exception(
                    f"[VgaPciIntel] Current platform NOT SUPPORTED for igd passthrough: use {' or '.join(qemu_platform.get_bios_boot_platform_list())} platform")
            if CurrentOs.is_uefi_boot():
                raise Exception(
                    f"[VgaPciIntel] Current platform NOT SUPPORTED for igd passthrough: use {' or '.join(qemu_platform.get_uefi_boot_platform_list())} platform")

    @staticmethod
    def is_my_instance(pci):
        return pci.class_code.is_vga() and pci.vendor_id.is_intel()

    def __check_passthrough_in_legacy_mode(self):
        if self.__cpu.is_intel_above_broadwell():
            return False  # UPT passthrough
        elif self.__cpu.is_intel_above_sandybridge():
            return True  # Legacy passthrough
        raise Exception(f"[VgaPciIntel] Passthrough NOT SUPPORTED: old CPU \"{self.__cpu.get_uarch_codename()}\"")


class UsbUhciPci(Pci):
    def __init__(self, pci):
        super().__init__()
        self._init(pci)

    def get_kernel_parameters(self):
        return ["usbcore.nousb"]

    @staticmethod
    def is_my_instance(pci):
        return pci.class_code.is_usb_uhci_controller(pci.prog_if)


class UsbOhciPci(Pci):
    def __init__(self, pci):
        super().__init__()
        self._init(pci)

    def get_kernel_parameters(self):
        return ["usbcore.nousb"]

    @staticmethod
    def is_my_instance(pci):
        return pci.class_code.is_usb_ohci_controller(pci.prog_if)


class UsbEhciPci(Pci):
    def __init__(self, pci):
        super().__init__()
        self._init(pci)

    def get_kernel_parameters(self):
        return ["usbcore.nousb"]

    @staticmethod
    def is_my_instance(pci):
        return pci.class_code.is_usb_ehci_controller(pci.prog_if)


class UsbXhciPci(Pci):
    def __init__(self, pci):
        super().__init__()
        self._init(pci)

    def get_kernel_parameters(self):
        return ["usbcore.nousb"]

    @staticmethod
    def is_my_instance(pci):
        return pci.class_code.is_usb_xhci_controller(pci.prog_if)


class IsaBridgePci(Pci):
    def __init__(self, pci):
        super().__init__()
        self._init(pci)

    @staticmethod
    def is_my_instance(pci):
        return pci.class_code.is_isa_bridge()


# fixme utopia Parser for command line
#   -<key1> <value1> -<key2> "<value1>" -<key2> '<value1>' -<key2> --<key3>=<value3> --<key3>="<value3>" --<key3>='<value3>'
# fixme utopia Parser for subvalue
#   <value>,<subkey1>=<subvalue1>,<subkey>=<subvalue2>,
#

# Рендер/парсинг для опций
# - shell
#   - минус/пробел
#   - минус-минус равно
#   - qemu suboptions, разделитель запятая
# - kernel parameters
#   - опция=значение,
#   - сабопция для модуля ядра опция.параметр=значение
#   - опция
# {
#   "option0": "value",
#   "option1": { "suboption1_0": { "suboption1_0_0": "value" } }
#   "": [ "pos_value0", "pos_value1" ] // Позиционные аргументы
# }
#

class Daemon:
    WATCHDOG_TIMEOUT_IN_SECONDS = 30

    class KillOpenVpnServer(asyncio.CancelledError):
        pass

    def __init__(self, open_vpn_config=OpenVpnConfig()):
        self.__open_vpn_config = open_vpn_config
        self.__my_ip_address_and_port = None

    async def run(self):
        while True:
            async with asyncio.TaskGroup() as group:
                await self.__refresh_external_ip_address_and_port()
                await self.__send_ovpn_after_reconfig()
                open_vpn_server_task = group.create_task(self.__init_vpn_server())
                group.create_task(self.__watchdog_loop(open_vpn_server_task))

    async def __init_vpn_server(self):
        server_config_path = OpenVpnServerConfigGenerator().generate()
        await OpenVpnServer(server_config_path).run()

    async def __refresh_external_ip_address_and_port(self):
        open_vpn_server_port = self.__open_vpn_config.get_server_port()
        self.__my_ip_address_and_port = MyExternalIpAddressAndPort(open_vpn_server_port).get()
        TextConfigWriter(self.__open_vpn_config.get_my_current_ip_address_and_port()).set(
            self.__my_ip_address_and_port)

    async def __send_ovpn_after_reconfig(self):
        user_name = "utopia"
        user_ovpn_file_path = OpenVpnClientConfigGenerator(self.__my_ip_address_and_port, user_name).generate()
        TelegramClient().send_file(user_ovpn_file_path)

    async def __watchdog_loop(self, open_vpn_server_task):
        with UdpWatchdog(self.__my_ip_address_and_port) as udp_watchdog:
            while udp_watchdog.watch():
                await asyncio.sleep(self.WATCHDOG_TIMEOUT_IN_SECONDS)
        await asyncio.sleep(self.WATCHDOG_TIMEOUT_IN_SECONDS)
        open_vpn_server_task.cancel()


class TcpPort:
    TCP_PORT_MIN = 1
    TCP_PORT_MAX = 65535

    SSH_PORT_DEFAULT = 22
    RDP_PORT_DEFAULT = 3389
    VNC_BASE_PORT_NUMBER = 5900

    def __init__(self, port):
        if not TcpPort.is_valid(port):
            raise Exception(f"TCP port FAIL: {port}")
        self.__port = int(port)

    def __str__(self):
        return str(self.__port)

    def __repr__(self):
        return self.__str__()

    def __int__(self):
        return int(self.__port)

    def __eq__(self, other):
        _other = None
        try:
            _other = TcpPort(other)
        except Exception:
            pass

        if not _other:
            return False

        return int(self) == int(_other)

    def is_ssh(self):
        return int(self) == TcpPort.SSH_PORT_DEFAULT

    def is_rdp(self):
        return int(self) == TcpPort.RDP_PORT_DEFAULT

    def is_vnc_base(self):
        return int(self) == TcpPort.VNC_BASE_PORT_NUMBER

    @staticmethod
    def is_valid(port):
        try:
            if port is None:
                return False

            port_as_int = int(port)
            if port_as_int < TcpPort.TCP_PORT_MIN:
                return False
            if port_as_int > TcpPort.TCP_PORT_MAX:
                return False

            return True
        except Exception:
            return False


class VmTcpForwarding:
    RETRY_COUNT = 30

    def __init__(self, vm_meta_data, local_network_if, input_port, output_port):
        self.__vm_meta_data = vm_meta_data
        self.__local_network_if = NetworkInterface(local_network_if)
        self.__input_port = input_port
        self.__output_port = TcpPort(output_port)
        atexit.register(self.clear_at_exit)

    def add(self):
        if not self.__is_valid_input_port():
            Logger.instance().debug(f"[VmTcpForwarding] TCP port forwarding DISCARDED")
            return
        Logger.instance().debug(
            f"[VmTcpForwarding] TCP port forwarding for vm \"{self.__vm_meta_data.get_name()}\": {self.__local_network_if}:{self.__input_port} --> {self.__get_vm_destination_ip_address_and_port()}")
        self.__iptables_rule()

    def add_with_retry(self):
        sleep_sec = 5
        for i in range(VmTcpForwarding.RETRY_COUNT):
            try:
                Logger.instance().debug(f"[VmTcpForwarding] {i + 1} Try TCP port forwarding")
                self.add()
                Logger.instance().debug(f"[VmTcpForwarding] TCP port forwarding OK")
                return
            except Exception as ex:
                Logger.instance().warning(f"[VmTcpForwarding] FAIL: {ex}")
                if i == VmTcpForwarding.RETRY_COUNT - 1:
                    Logger.instance().error(f"[VmTcpForwarding] TCP port forwarding ATTEMPTS OVER")
                    return
                time.sleep(sleep_sec)

    def clear(self):
        if not self.__is_valid_input_port():
            return
        self.__iptables_rule(clear=True)

    def clear_at_exit(self):
        try:
            self.clear()
        except Exception as ex:
            Logger.instance().error(f"[VmTcpForwarding] FAIL: {ex}")

    def __is_valid_input_port(self):
        return TcpPort.is_valid(self.__input_port)

    def __iptables_rule(self, clear=False):
        # sudo iptables -t nat -A PREROUTING -i {self.__local_network_if} -p tcp --dport {self.__input_port} -j DNAT --to {self.__vm_metadata.get_ip_address()}:{self.__output_port}

        # Живой пример
        # sudo iptables -t nat -A PREROUTING -i wlp0s20f3 -p tcp --dport 2222 -j DNAT --to 172.20.47.124:22

        table = iptc.Table(iptc.Table.NAT)
        chain = iptc.Chain(table, "PREROUTING")

        rule = iptc.Rule()
        rule.in_interface = str(self.__local_network_if)
        rule.protocol = "tcp"

        match = iptc.Match(rule, "tcp")
        match.dport = str(self.__input_port)
        rule.add_match(match)

        target = iptc.Target(rule, "DNAT")
        target.to_destination = str(self.__get_vm_destination_ip_address_and_port())
        rule.target = target

        if clear:
            chain.delete_rule(rule)
        else:
            chain.insert_rule(rule)
        table.commit()
        Logger.instance().debug(
            f"[VmTcpForwarding] Table NAT after setup {iptc.easy.dump_table(iptc.Table.NAT, ipv6=False)}")

    def __get_vm_destination_ip_address_and_port(self):
        return IpAddressAndPort(self.__vm_meta_data.get_ip_address_strong(), self.__output_port)


class VmSshForwarding(VmTcpForwarding):
    def __init__(self, vm_meta_data, local_network_if, input_port):
        super().__init__(vm_meta_data=vm_meta_data, local_network_if=local_network_if, input_port=input_port,
                         output_port=TcpPort.SSH_PORT_DEFAULT)

    pass


class VmRdpForwarding(VmTcpForwarding):
    def __init__(self, vm_meta_data, local_network_if, input_port):
        super().__init__(vm_meta_data=vm_meta_data, local_network_if=local_network_if, input_port=input_port,
                         output_port=TcpPort.RDP_PORT_DEFAULT)

    pass


class EscapeLiteral:
    DECODE_TABLE_DEFAULT = [("\\\\", "\\"), ("\\\"", "\""), ("\\\'", "'"), ("\\n", "\n"),
                            ("\\r", "\r")]

    ENCODE_TABLE_DEFAULT = [("\\", "\\\\"), ("\"", "\\\""), ("'", "\\\'"), ("\n", "\\n"),
                            ("\r", "\\r")]

    def __init__(self, decode_table=DECODE_TABLE_DEFAULT,
                 encode_table=ENCODE_TABLE_DEFAULT):
        self.__decode_table = decode_table
        self.__encode_table = encode_table

    def decode(self, target_string):
        result = target_string
        for escape_literal, replace_literal in self.__decode_table:
            result = result.replace(escape_literal, replace_literal)
        return result

    def encode(self, target_string):
        result = target_string
        for replace_literal, escape_literal in self.__encode_table:
            result = result.replace(replace_literal, escape_literal)
        return result


class UnitTest_EscapeLiteral(unittest.TestCase):

    def self_test(self):
        target_string = "\rhello\\\n\"world!\'\n\r\\hello world"

        escape_literal = EscapeLiteral()
        encoded_string = escape_literal.encode(target_string)
        decoded_string = escape_literal.decode(encoded_string)
        self.assertEqual(target_string, decoded_string)


class NoneFromString:
    __NONE_AS_STRING = {"null": None, "none": None}

    def __init__(self):
        pass

    def get(self, target_string):
        if target_string.strip().lower() in self.__NONE_AS_STRING:
            return True, None

        return False, target_string


class BoolFromString:
    __BOOL_AS_STRING = {"yes": True, "true": True, "on": True, "no": False, "false": False, "off": False}

    def __init__(self, is_bool_as_int=True):
        self.__is_bool_as_int = bool(is_bool_as_int)

    def get(self, target_string):
        _target_string = target_string.strip().lower()
        if _target_string in self.__BOOL_AS_STRING:
            result = self.__BOOL_AS_STRING[_target_string]
            if self.__is_bool_as_int:
                result = int(result)
            return True, result

        return False, target_string


class IntFromString:
    def __init__(self):
        pass

    def get(self, target_string):
        return self.as_int(target_string)

    def as_int(self, target_string):
        is_good, result = self.as_decimal_int(target_string)
        if is_good:
            return is_good, result

        is_good, result = self.as_hexadecimal_int(target_string)
        if is_good:
            return is_good, result

        is_good, result = self.as_binary_int(target_string)
        if is_good:
            return is_good, result

        return self.as_octal_int(target_string)

    def as_decimal_int(self, target_string):
        if not BitUtils.is_decimal(target_string):
            return False, target_string
        return True, int(target_string.strip().lower(), BitUtils.DECIMAL_BASE)

    def as_hexadecimal_int(self, target_string):
        if not BitUtils.is_hexadecimal(target_string):
            return False, target_string
        return True, int(target_string.strip().lower(), BitUtils.HEXADECIMAL_BASE)

    def as_binary_int(self, target_string):
        if not BitUtils.is_binary(target_string):
            return False, target_string
        return True, int(target_string.strip().lower(), BitUtils.BINARY_BASE)

    def as_octal_int(self, target_string):
        if not BitUtils.is_octal(target_string):
            return False, target_string
        return True, int(target_string.strip().lower(), BitUtils.OCTAL_BASE)


class FloatFromString:
    def __init__(self):
        pass

    def get(self, target_string):
        return self.as_float(target_string)

    def as_float(self, target_string):
        try:
            return True, float(target_string.strip().lower())
        except Exception as ex:
            return False, target_string


class NumberFromString:
    def __init__(self, int_from_string=IntFromString(), float_from_string=FloatFromString()):
        self.__int_from_string = int_from_string
        self.__float_from_string = float_from_string

    def get(self, target_string):
        is_good, result = self.__int_from_string.get(target_string)
        if is_good:
            return is_good, result

        return self.__float_from_string.get(target_string)


class StringFromString:
    def __init__(self, escape_literal=EscapeLiteral()):
        self.__escape_literal = escape_literal

    def get(self, target_string):
        if len(target_string) == 0:
            return True, target_string

        if (target_string[0] == '"' and target_string[-1] == '"') or (
                target_string[0] == "'" and target_string[-1] == "'"):
            target_string = target_string[1:-1]
            return True, self.__escape_literal.decode(target_string)

        return False, self.__escape_literal.decode(target_string)


class FromString:
    def __init__(self, is_try_parse_string=True,
                 string_from_string=StringFromString(),
                 number_from_string=NumberFromString(),
                 bool_from_string=BoolFromString(),
                 none_from_string=NoneFromString()):
        self.__is_try_parse_string = is_try_parse_string
        self.__string_from_string = string_from_string
        self.__number_from_string = number_from_string
        self.__bool_from_string = bool_from_string
        self.__none_from_string = none_from_string

    def get(self, target_string):
        if not isinstance(target_string, str):
            Logger.instance().debug(f"[FromString] Parse NOT STRING: {target_string}")
            return target_string

        result_as_string = target_string

        if self.__string_from_string is not None:
            is_good, result_as_string = self.__string_from_string.get(target_string)
            if is_good and not self.__is_try_parse_string:
                Logger.instance().debug(f"[FromString] Parse as string: {target_string} / {result_as_string}")
                return result_as_string

        if self.__number_from_string is not None:
            is_good, result = self.__number_from_string.get(result_as_string)
            if is_good:
                Logger.instance().debug(f"[FromString] Parse as number: {result} / {result_as_string}")
                return result

        if self.__bool_from_string is not None:
            is_good, result = self.__bool_from_string.get(result_as_string)
            if is_good:
                Logger.instance().debug(f"[FromString] Parse as bool: {result} / {result_as_string}")
                return result

        if self.__none_from_string is not None:
            is_good, result = self.__none_from_string.get(result_as_string)
            if is_good:
                Logger.instance().debug(f"[FromString] Parse as none: {result} / {result_as_string}")
                return result

        return result_as_string


# \[(?=[\w\.]{1,16}\])(?>\.?[\w]+)+\]
# https://regex101.com/r/ZLjLC2/1
class ConfigParameterNameParser:
    __NAME_LENGTH_MIN = 1

    def __init__(self, name_length_max=64, is_match_start_of_string=True, underscore_character_set="_",
                 subname_separator="",
                 subname_count_max=0):
        self.__name_length_max = name_length_max
        self.__is_match_start_of_string = is_match_start_of_string
        self.__underscore_character_set = RegexConstants.character_set_escape(underscore_character_set)
        self.__subname_separator = RegexConstants.character_set_escape(subname_separator, is_remove_duplicate=False)
        self.__subname_count_max = subname_count_max

        if self.__name_length_max < self.__NAME_LENGTH_MIN:
            self.__name_length_max = self.__NAME_LENGTH_MIN

        if self.__subname_count_max < 0:
            self.__subname_count_max = 0

    def get_subname_count_max(self):
        return self.__subname_count_max

    def get_regex(self, with_capture=True):
        begin_capture = "(" if with_capture else ""
        end_capture = ")" if with_capture else ""
        start_of_string = "^" if self.__is_match_start_of_string else ""
        result = f"{start_of_string}{begin_capture}{self.__get_regex_template(with_capture=False)}"
        if self.__subname_count_max > 0:
            result += f"{RegexConstants.atomic_group(f'{self.__subname_separator}{self.__get_regex_template(with_capture)}')}{{0,{self.__subname_count_max}}}"
        return f"{result}{end_capture}"

    def get_regex_for_name(self, name):
        start_of_string = "^" if self.__is_match_start_of_string else ""
        return f"{start_of_string}{name}"

    def check_name(self, name):
        regex = re.compile(self.get_regex(with_capture=False))
        match = regex.match(name)
        if match is None:
            return False
        return True

    def __get_regex_template(self, with_capture):
        begin_capture = "(" if with_capture else ""
        end_capture = ")" if with_capture else ""
        return f"{begin_capture}[a-zA-Z{self.__underscore_character_set}][a-zA-Z0-9{self.__underscore_character_set}]{{0,{self.__name_length_max - self.__NAME_LENGTH_MIN}}}{end_capture}"


class ConfigNameValueDelimiterParser:
    def __init__(self, delimiter="=", is_delimiter_optional=False):
        self.__delimiter = delimiter
        self.__is_delimiter_optional = is_delimiter_optional

    def get_regex(self):
        if self.__is_delimiter_optional:
            return f"(?>{self.__delimiter}|)"
        return f"{self.__delimiter}"

    def get_delimiter(self):
        return self.__delimiter


class ConfigParameterValueParser:
    __DOUBLE_QUOTE = "\""
    __SINGLE_QUOTE = "'"
    __BACK_SLASH_ESCAPE = fr"\\"
    __DOUBLE_QUOTE_ESCAPE = fr"{__BACK_SLASH_ESCAPE}{__DOUBLE_QUOTE}"
    __SINGLE_QUOTE_ESCAPE = fr"{__BACK_SLASH_ESCAPE}{__SINGLE_QUOTE}"

    def __init__(self, is_match_end_of_string=True):
        self.__is_match_end_of_string = is_match_end_of_string

    def get_regex(self, with_capture=True):
        regex_with_double_quote = self.__get_regex_with_quotes(self.__DOUBLE_QUOTE, self.__DOUBLE_QUOTE_ESCAPE,
                                                               with_capture)
        regex_with_single_quote = self.__get_regex_with_quotes(self.__SINGLE_QUOTE, self.__SINGLE_QUOTE_ESCAPE,
                                                               with_capture)
        regex_simple = self.__get_regex_simple(with_capture)
        return fr"(?>{regex_with_double_quote}|{regex_with_single_quote}|{regex_simple})"

    def __get_regex_with_quotes(self, quote, quote_escape, with_capture):
        begin_mark = quote
        end_mark = quote
        unacceptable_symbols = quote
        escape = quote_escape
        return self.__get_regex_template(begin_mark, end_mark, unacceptable_symbols, escape, with_capture)

    def __get_regex_simple(self, with_capture):
        begin_mark = ""
        end_mark = ""
        unacceptable_symbols = fr"{RegexConstants.WHITESPACES}{self.__DOUBLE_QUOTE}{self.__SINGLE_QUOTE}"
        escape = fr"{self.__DOUBLE_QUOTE_ESCAPE}|{self.__SINGLE_QUOTE_ESCAPE}"
        return self.__get_regex_template(begin_mark, end_mark, unacceptable_symbols, escape, with_capture)

    def __get_regex_template(self, begin_mark, end_mark, unacceptable_symbols, escape, with_capture):
        back_slash_escape = self.__BACK_SLASH_ESCAPE

        begin_capture = "(" if with_capture else ""
        end_capture = ")" if with_capture else ""
        end_of_string = "$" if self.__is_match_end_of_string else ""
        return rf"{begin_capture}{begin_mark}(?>[^{unacceptable_symbols}{back_slash_escape}]*(?>{escape}|{back_slash_escape})*)*{end_mark}{end_capture}{RegexConstants.WHITESPACE_CHARACTER_SET}*{end_of_string}"


class NoSection:
    def get_sections(self, content):
        return {"": {"index": [(0, len(content))], "content": content}}


class SectionWithoutSubsections(NoSection):
    def __init__(self, parameter_name_parser=ConfigParameterNameParser(is_match_start_of_string=False)):
        super().__init__()
        self.__parameter_name_parser = parameter_name_parser

    def get_sections(self, content):
        result = {}  # fixme utopia Нужно сохранть порядок следования секций чтобы правильно вычислить положение отностительных подсекций для ini файлов
        last_section_name = None
        for match in re.finditer(self.get_section_name_regex(), content, flags=re.MULTILINE):
            section_name = match.group(0)
            data_index_begin = len(content) if len(content) == match.end() else match.end() + 1

            if last_section_name is not None:
                result[last_section_name]["index"][-1][1] = match.start()

            if section_name in result:
                result[section_name]["index"].append((data_index_begin, None))
            else:
                result.update({section_name: {"index": [(data_index_begin, None)]}})
            last_section_name = section_name

        if last_section_name is not None:
            result[last_section_name]["index"][-1][1] = len(content)

        if len(result) == 0:
            return NoSection.get_sections(content)

        for section_name, description in result.items():
            for index_begin, index_end in description["index"]:
                description["content"] += content[index_begin:index_end]

        return result

    def get_section_name_regex(self):
        return fr"^\[{self.__parameter_name_parser.get_regex()}\]{RegexConstants.ZERO_OR_MORE_WHITESPACES}$"


class Section:
    def __init__(self):
        print("ttt")

    def get_sections(self, content):
        # Сформировать при помощи регулярки посекционно без разбиения по подсекциям
        # Разбить по подсекциям
        return {}

    # https://docs.python.org/3/library/re.html#finding-all-adverbs-and-their-positions
    #   [
    #     {
    #        "name": (String) // Если секции не используются то заполнить пустой строкой, подсекции в таком случае невозможны
    #        "index":
    #        [
    #          {
    #            "begin": (Int32),
    #            "end":   (Int32)
    #          },
    #          { ... }
    #        ],
    #        "content": (String) // Склеенные подстрочки по index
    #        "subsection": // Может быть пусто
    #        {
    #          "name": (String)
    #          "index":
    #          [
    #            {
    #              "begin": (Int32),
    #              "end":   (Int32)
    #            },
    #            { ... }
    #          ],
    #          "content": (String) // Склеенные подстрочки по index
    #          "subsection": ... // Может быть пусто
    #        }
    #     },
    #     { ... }
    #   ]


class ShellSerializer:
    KEY_VALUE_SEPARATOR_TABLE_DEFAULT = [{"prefix": "--", "separator": "="},
                                         {"prefix": "", "separator": " "}]

    def __init__(self, quotes_for_string_value='"',
                 key_value_separator_table=KEY_VALUE_SEPARATOR_TABLE_DEFAULT, pair_separator=" ",
                 escape_literal=EscapeLiteral(), nested_serializer=None, nested_key_value_separator=" ",
                 nested_escape_literal=None):
        self.__quotes_for_string_value = quotes_for_string_value
        self.__key_value_separator_table = key_value_separator_table
        self.__pair_separator = pair_separator
        self.__escape_literal = escape_literal
        self.__nested_serializer = nested_serializer
        self.__nested_key_value_separator = nested_key_value_separator
        self.__nested_escape_literal = nested_escape_literal

    def serialize(self, config):
        result = self.__serialize_impl(config)
        if result.endswith(self.__pair_separator):
            result = result[:len(result) - len(self.__pair_separator)]
        return result

    def __serialize_impl(self, config):
        result = ""
        if isinstance(config, list):
            for item in config:
                result = f"{result}{self.__serialize_impl(item)}"
        elif isinstance(config, dict):
            for key, value in config.items():
                if isinstance(value, dict) or isinstance(value, list):
                    result = f"{result}{self.__serialize_nested_impl(key, value)}"
                else:
                    result = f"{result}{self.__serialize_key_value(key, value)}"
        else:
            result = f"{result}{self.__serialize_key(config)}"
        return result

    def __serialize_nested_impl(self, key, value):
        if self.__nested_serializer is not None:
            return self.__serialize_key_value(key, self.__nested_serializer.serialize(value), is_nested=True)
        raise Exception(f"Nested serialization policy NOT FOUND: {key}: {value}")

    def __serialize_key(self, key):
        if len(key) == 0:
            return ""
        return f"{key}{self.__pair_separator}"

    def __serialize_key_value(self, key, value, is_nested=False):
        separator = self.__get_nested_separator(key) if is_nested else self.__get_separator(key)
        return f"{key}{separator}{self.__serialize_value(value, is_nested)}{self.__pair_separator}"

    def __serialize_value(self, value, is_nested=False):
        result = str(value)
        if isinstance(value, str):
            result = self.___encode_nested_literal(result) if is_nested else self.__encode_literal(result)
            result = f"{self.__quotes_for_string_value}{result}{self.__quotes_for_string_value}"
        return result

    def __get_separator(self, key):
        for __key_value_separator in self.__key_value_separator_table:
            if str(key).startswith(__key_value_separator["prefix"]):
                return __key_value_separator['separator']
        return ""

    def __get_nested_separator(self, key):
        if self.__nested_key_value_separator is None:
            return ""
        return str(self.__nested_key_value_separator)

    def __encode_literal(self, value):
        if self.__escape_literal is None:
            return value
        return self.__escape_literal.encode(value)

    def ___encode_nested_literal(self, value):
        if self.__nested_escape_literal is None:
            return value
        return self.__nested_escape_literal.encode(value)


class UnitTest_ShellSerializer(unittest.TestCase):

    def test_serialize(self):
        ref_table = {
            '--device="test_device" key "\\\\\\n\\"hello world!!\\"\\r" key1 --device="test_device" -device2 "test_device2" -device3 "test_device3" --key2=15 --key3=18.7 --key4=True': [
                {"--device": "test_device"},
                {"key": "\\\n\"hello world!!\"\r"},
                "key1",
                {"--device": "test_device", "-device2": "test_device2", "-device3": "test_device3"},
                {"--key2": 15, "--key3": 18.7, "--key4": True},
            ],
            '--device="test_device" --device1="test_device1"':
                {
                    "--device": "test_device",
                    "--device1": "test_device1"
                }
        }

        serializer = ShellSerializer()
        for config_serialized, config in ref_table.items():
            result = serializer.serialize(config)
            self.assertEqual(result, config_serialized, f"\n\nRESULT\n{result}\n\nREF\n{config_serialized}")

    def test_nested_fail(self):
        config = {"-device": {"subdevice": "test_device"}}

        serializer = ShellSerializer()
        self.assertRaises(Exception, serializer.serialize, config)


class QemuSerializer(ShellSerializer):
    class QemuEscapeLiteral(EscapeLiteral):
        def __init__(self):
            super().__init__(encode_table=[(",", ",,")])

    def __init__(self):
        super().__init__(nested_serializer=ShellSerializer(quotes_for_string_value="",
                                                           key_value_separator_table=[
                                                               {"prefix": "", "separator": "="}],
                                                           pair_separator=",",
                                                           escape_literal=QemuSerializer.QemuEscapeLiteral(),
                                                           nested_serializer=ShellSerializer(quotes_for_string_value="",
                                                                                             key_value_separator_table=[
                                                                                                 {"prefix": "",
                                                                                                  "separator": "="}],
                                                                                             pair_separator=",",
                                                                                             escape_literal=QemuSerializer.QemuEscapeLiteral()),
                                                           nested_key_value_separator=","
                                                           ))


class UnitTest_QemuSerializer(unittest.TestCase):

    def test_serialize(self):
        ref_table = {
            '-enable-kvm -m 8192 -netdev "tap,ifname=homevpn-tap2,script=no,downscript=no,id=homevpn-tap2-id" -device "virtio-net,netdev=homevpn-tap2-id,mac=ee:08:bf:ab:45:42" -vnc "127.0.0.1:2" -drive "file=/home/utopia/HomeVpn/vm ,,/win10.img,media=disk,if=virtio" -cpu "Icelake-Server-v5" -smp "cpus=4,sockets=1,cores=2,threads=2,maxcpus=4" -device "virtio-vga-gl" -display "sdl,gl=on" -usb -device "usb-host,vendorid=0x045E,productid=0x00DB" -usb -device "usb-host,vendorid=0x0BDA,productid=0x8771" -usb -device "usb-host,vendorid=0x046D,productid=0xC05B" -usb -device "usb-host,vendorid=0x258A,productid=0x0302" -monitor "telnet:127.0.0.1:55555,server,nowait"': [
                "-enable-kvm",
                {"-m": 8192},
                {"-netdev": {"tap":
                                 {"ifname": "homevpn-tap2", "script": "no", "downscript": "no",
                                  "id": "homevpn-tap2-id"}}},
                {"-device": {"virtio-net": {"netdev": "homevpn-tap2-id", "mac": "ee:08:bf:ab:45:42"}}},
                {"-vnc": "127.0.0.1:2"},
                {"-drive": {"file": "/home/utopia/HomeVpn/vm ,/win10.img", "media": "disk", "if": "virtio"}},
                {"-cpu": "Icelake-Server-v5"},
                {"-smp": {"cpus": 4, "sockets": 1, "cores": 2, "threads": 2, "maxcpus": 4}},
                {"-device": "virtio-vga-gl"},
                {"-display": {"sdl": {"gl": "on"}}},
                "-usb",
                {"-device": {"usb-host": {"vendorid": "0x045E", "productid": "0x00DB"}}},
                "-usb",
                {"-device": {"usb-host": {"vendorid": "0x0BDA", "productid": "0x8771"}}},
                "-usb",
                {"-device": {"usb-host": {"vendorid": "0x046D", "productid": "0xC05B"}}},
                "-usb",
                {"-device": {"usb-host": {"vendorid": "0x258A", "productid": "0x0302"}}},
                {"-monitor": ["telnet:127.0.0.1:55555", "server", "nowait"]}
            ]
        }

        serializer = QemuSerializer()
        for config_serialized, config in ref_table.items():
            result = serializer.serialize(config)
            self.assertEqual(result, config_serialized, f"\n\nRESULT\n{result}\n\nREF\n{config_serialized}")


class IniSerializer:
    def __init__(self, is_compact_sections=False, quotes_for_string_value='"', subsection_separator=".",
                 key_value_separator="=", pair_separator="\n", escape_literal=EscapeLiteral()):
        self.__is_compact_sections = is_compact_sections  # fixme utopia Не реализовано
        self.__quotes_for_string_value = quotes_for_string_value
        self.__subsection_separator = subsection_separator
        self.__key_value_separator = key_value_separator
        self.__pair_separator = pair_separator
        self.__escape_literal = escape_literal

    def serialize(self, config):
        result = self.__serialize_impl(config, section_list=[])
        if result.endswith(self.__pair_separator):
            result = result[:len(result) - len(self.__pair_separator)]
        return result

    def __serialize_impl(self, config, section_list, is_same_section=True):
        result = ""
        if isinstance(config, list):
            for item in config:
                result = f"{result}{self.__serialize_impl(item, section_list=section_list, is_same_section=is_same_section)}"
        elif isinstance(config, dict):
            for key, value in config.items():
                if isinstance(value, dict) or isinstance(value, list):
                    section_list_new = section_list.copy()
                    section_list_new.append(key)
                    result = f"{result}{self.__serialize_impl(value, section_list=section_list_new, is_same_section=False)}"
                else:
                    result = f"{result}{self.__serialize_section_name(section_list, is_same_section)}{self.__serialize_key_value(key, value)}"
                    is_same_section = True
        else:
            result = f"{result}{self.__serialize_key(config)}"
        return result

    def __serialize_section_name(self, section_list, is_same_section):
        if len(section_list) == 0 or is_same_section:
            return ""
        return f"[{self.__subsection_separator.join(section_list)}]{self.__pair_separator}"

    def __serialize_key(self, key):
        if len(key) == 0:
            return ""
        return f"{key}{self.__key_value_separator}{self.__pair_separator}"

    def __serialize_key_value(self, key, value):
        return f"{key}{self.__key_value_separator}{self.__serialize_value(value)}{self.__pair_separator}"

    def __serialize_value(self, value):
        result = str(value)
        if isinstance(value, str):
            result = f"{self.__quotes_for_string_value}{self.__encode_literal(result)}{self.__quotes_for_string_value}"
        return result

    def __encode_literal(self, value):
        if self.__escape_literal is None:
            return value
        return self.__escape_literal.encode(value)


class UnitTest_IniSerializer(unittest.TestCase):

    def test_serialize(self):
        config_ref = '''key1="string_value1"
key2="\\\\\\n\\"hello world!!\\"\\r"
key3=
[section_name1]
key1_1=1.1
[section_name1.section_name1_1.section_name1_1_1]
key1_1_1=False
[section_name1]
key1_2=147
key1_3="None"'''

        ref_table = {
            config_ref: [
                {"key1": "string_value1"},
                {"key2": "\\\n\"hello world!!\"\r"},
                "key3",
                {
                    "section_name1":
                        [
                            {"key1_1": 1.1},
                            {
                                "section_name1_1":
                                    {
                                        "section_name1_1_1":
                                            [
                                                {"key1_1_1": False}
                                            ]
                                    },
                                "key1_2": 147,
                                "key1_3": "None"
                            }
                        ]
                }
            ]
        }

        serializer = IniSerializer()
        for config_serialized, config in ref_table.items():
            result = serializer.serialize(config)
            self.assertEqual(result, config_serialized, f"\n\nRESULT\n{result}\n\nREF\n{config_serialized}")


# fixme utopia Что требуется
# ++1) парсинг из строки
# ++2) bool --> int
# ++3) Нормализатор для мержинга словарей
# 3.1) юнит тесты для нормализатора
# 4) ShellSerializer умеет обрабатывать ast
# 5) субпарсер для массивов значений параметров ядра
# 6) субпарсер для вложенных словарей параметров ядра (video=vesafb:off,efifb:off и pcie_acs_override=downstream,id:8086:1234,8086:4321)
# 7) мержератор для параметров ядра для класса Grub
class ConfigParser:
    def __init__(self, name_parser=ConfigParameterNameParser(), delimiter_parser=ConfigNameValueDelimiterParser(),
                 value_parser=ConfigParameterValueParser(), from_string=FromString(), escape_literal=EscapeLiteral()):
        self.__name_parser = name_parser
        self.__delimiter_parser = delimiter_parser
        self.__value_parser = value_parser
        self.__from_string = from_string
        self.__escape_literal = escape_literal

    def get_value(self, name, content):
        return self.__from_string.get(self.get_value_as_is(name, content))

    def get_value_as_is(self, name, content):
        regex = re.compile(self.get_regex_for_search_value_by_name(name), re.MULTILINE)
        regex_result = regex.search(content)
        if regex_result is None:
            return None

        for group in regex_result.groups():
            if group is not None:
                return group

        return None

    def find_all(self, content, value_as_is=False, as_ast=False):
        result = dict()
        last_end = 0
        index = 0
        for match in re.finditer(self.get_regex(), content, flags=re.MULTILINE):
            name = match.group(1)
            value_start_index = 2  # match для всей регулярки (match.group(0)) + имя параметра (match.group(1))
            for i in range(value_start_index + self.__name_parser.get_subname_count_max(), match.lastindex + 1):
                if match.group(i) is not None:
                    value = match.group(i)
                    if bool(as_ast) and (last_end < match.start(0)):
                        result[index] = content[last_end:match.start(0)]
                        index += 1
                    last_end = match.end(i)
                    result[name] = value if value_as_is else self.__from_string.get(value)
                    break
        if bool(as_ast) and (last_end < len(content)):
            result[index] = content[last_end:]

        return result

    def remove_by_name(self, name, content):
        empty_line = ""
        regex = re.compile(self.get_regex_for_remove_by_name(name), re.MULTILINE)
        return regex.sub(empty_line, content)

    def add_or_update(self, name, value, content, with_quotes=True):
        value = self.__escape_literal.encode(value)
        value = f'"{value}"' if with_quotes else str(value)

        result = ""
        last_end = 0
        for match in re.finditer(self.get_regex_for_search_value_by_name(name), content, flags=re.MULTILINE):
            for i in range(1, match.lastindex + 1):
                if match.group(i) is not None:
                    result += content[last_end:match.start(i)] + value
                    last_end = match.end(i)
        result += content[last_end:]
        if last_end > 0:
            return result
        if len(result) > 0 and result[-1] != "\n":
            result += "\n"

        result += f"{name}{self.__delimiter_parser.get_delimiter()}{value}"
        return result

    def get_regex(self):
        return self.__get_regex_template(self.__name_parser.get_regex())

    def get_regex_for_search_value_by_name(self, name):
        return self.__get_regex_template(self.__name_parser.get_regex_for_name(name))

    def get_regex_for_remove_by_name(self, name):
        result = self.__get_regex_template(self.__name_parser.get_regex_for_name(name), with_value_capture=False)
        return f"({result})"

    def __get_regex_template(self, name_template, with_value_capture=True):
        return f"{name_template}{self.__delimiter_parser.get_regex()}{self.__value_parser.get_regex(with_value_capture)}"


class UnitTest_ConfigParser(unittest.TestCase):

    def test_parse(self):
        ref_table = {
            "a=b\nc=d\nhello=123\nstring=\"this is string in double quotes\"\nis_none=nOnE": {"a": "b", "c": "d",
                                                                                              "hello": 123,
                                                                                              "string": "this is string in double quotes",
                                                                                              "is_none": None}
        }

        config_parser = ConfigParser()
        for content, key_value in ref_table.items():
            for key, value in key_value.items():
                self.assertEqual(config_parser.get_value(key, content), value)

    def test_add_or_update(self):
        ref_table = [
            {
                "key": "key",
                "new_value": "\'new_value\n\r\"",
                "test_config": "key=value\nkey2=""\nkey=\"value2\"",
                "with_quotes": True,
                "expected_result": "key=\"\\\'new_value\\n\\r\\\"\"\nkey2=""\nkey=\"\\\'new_value\\n\\r\\\"\""
            },
            {
                "key": "key",
                "new_value": "hello",
                "test_config": "",
                "with_quotes": True,
                "expected_result": "key=\"hello\""
            },
            {
                "key": "key",
                "new_value": "hello",
                "test_config": "key2=value2",
                "with_quotes": True,
                "expected_result": "key2=value2\nkey=\"hello\""
            },
            {
                "key": "key",
                "new_value": "hello",
                "test_config": "key2=value2\n",
                "with_quotes": True,
                "expected_result": "key2=value2\nkey=\"hello\""
            },
            {
                "key": "key",
                "new_value": "hello",
                "test_config": "key2=value2\n  ",
                "with_quotes": False,
                "expected_result": "key2=value2\n  \nkey=hello"
            }
        ]

        config_parser = ConfigParser()
        for item in ref_table:
            result = config_parser.add_or_update(item["key"], item["new_value"], item["test_config"],
                                                 item["with_quotes"])
            expected_result = item["expected_result"]
            self.assertEqual(result,
                             expected_result, f"\n\nRESULT\n{result}\n\nREF\n{expected_result}")


class LinuxKernelParamsParser(ConfigParser):
    def __init__(self):
        super().__init__(
            name_parser=ConfigParameterNameParser(is_match_start_of_string=False, underscore_character_set="_-",
                                                  subname_separator=".",
                                                  subname_count_max=1),
            delimiter_parser=ConfigNameValueDelimiterParser(is_delimiter_optional=True),
            value_parser=ConfigParameterValueParser(is_match_end_of_string=False))


class Normalizer:
    def __init__(self):
        pass

    class EmptyValue:
        pass

    def normalize(self, config):
        result_normalize = dict()
        self.__normalize_recursive(config, result_normalize)
        result = []
        self.__normalize_recursive2(result_normalize, result)
        return result

    def __normalize_recursive(self, config, result_ref, key_list=list()):
        if isinstance(config, dict):
            for key, value in config.items():
                if not key in result_ref:
                    result_ref[key] = dict()

                _key_list = key_list.copy()
                _key_list.append(key)
                self.__normalize_recursive(value, result_ref[key], _key_list)
        elif isinstance(config, list):
            for item in config:
                self.__normalize_recursive(item, result_ref, key_list)
        elif isinstance(config, str):  # Ключи без значений
            _key_list = key_list
            if not _key_list:
                _key_list = [config]
            result_ref[config] = Normalizer.EmptyValue()

    def __normalize_recursive2(self, config, result_ref):
        if isinstance(config, dict):
            result = []
            for key, value in config.items():
                if isinstance(value, Normalizer.EmptyValue):
                    result.append(key)
                else:
                    tmp = []
                    self.__normalize_recursive2(value, tmp)
                    if len(tmp) == 0:
                        result.append({key: {}})
                    elif len(tmp) == 1:
                        result.append({key: tmp[0]})
                    elif len(tmp) > 1:
                        result.append({key: tmp})
            if len(result) == 1:
                result_ref.append(result[0])
            elif len(result) > 1:
                result_ref.extend(result)


# fixme utopia Подать пустую строку в словаре
class UnitTest_Normalizer(unittest.TestCase):
    def test_normalize(self):
        ref_table = [
            {
                "expected":
                    [
                        "vfio",
                        {"vfio-pci": ["1", "2", "3", "4"]},
                        {"module-blacklist": ["i915", "kernel_module",
                                              "kernel_module2",
                                              "kernel_module3",
                                              "kernel_module4"]},
                        {"i915.modeset": "0"},
                        "mdev",
                        {"iommu": "pt"},
                        {"intel_iommu": "on"}
                    ],

                "input":
                    [
                        "vfio",
                        {"vfio-pci": ["1", "2", "3"]},
                        {"vfio-pci": ["1", "2", "3", ["4"]]},
                        {"module-blacklist": [
                            "i915",
                            "kernel_module"]},
                        {"module-blacklist": [
                            "i915",
                            "kernel_module2"]},
                        {"module-blacklist": "kernel_module3"},
                        {"module-blacklist": [
                            "kernel_module4"]},
                        {"module-blacklist": [
                            "kernel_module3"]},
                        {"i915.modeset": "0"},
                        "mdev",
                        {"iommu": "pt",
                         "intel_iommu": "on"}
                    ]
            },

            {
                "expected":
                    [
                        {"key": {"subkey": ["value1", "value2"]}},
                        {"key2": [{"subkey2": {}}, {"subkey3": {}}]}
                    ],

                "input":
                    {"key": [{"subkey": "value1"}, {"subkey": "value2"}, {"subkey": "value1"}],
                     "key2": {"subkey2": {}, "subkey3": []}}
            },

            {
                "expected":
                    ["key"],

                "input":
                    "key"
            }
        ]

        for test in ref_table:
            _input = test["input"]
            expected = test["expected"]
            normalizer = Normalizer()
            result = normalizer.normalize(_input)
            self.assertEqual(result, expected, f"\n\nRESULT\n{result}\n\nEXPECTED\n{expected}")


class LinuxKernelParamsSerializer(ShellSerializer):
    def __init__(self, key_modify_table=[("-", "_")]):
        super().__init__(key_value_separator_table=[
            {"prefix": "", "separator": "="}], nested_key_value_separator="=",
            nested_serializer=ShellSerializer(quotes_for_string_value="",
                                              key_value_separator_table=[
                                                  {"prefix": "", "separator": ":"}],
                                              pair_separator=",",
                                              nested_serializer=ShellSerializer(quotes_for_string_value="",
                                                                                key_value_separator_table=[
                                                                                    {"prefix": "", "separator": "?"}],
                                                                                pair_separator=","
                                                                                ),
                                              nested_key_value_separator=":"
                                              ))
        self.__modify_key_policy = EscapeLiteral(encode_table=key_modify_table)
        self.__normalizer = Normalizer()

    def serialize(self, config):
        config_copy = copy.deepcopy(config)
        self.__modify_config_keys(config_copy)
        return super().serialize(self.__normalizer.normalize(config_copy))

    def __modify_config_keys(self, config_ref):
        if isinstance(config_ref, dict):
            config_dict_with_new_keys = dict()
            for key, value in config_ref.items():
                config_dict_with_new_keys[self.__modify_key_policy.encode(key)] = value
            config_ref.clear()
            config_ref.update(config_dict_with_new_keys)

            for key, value in config_ref.items():
                self.__modify_config_keys(value)
        elif isinstance(config_ref, list):
            for item in config_ref:
                self.__modify_config_keys(item)


class UnitTest_LinuxKernelParamsSerializer(unittest.TestCase):

    def test_serialize(self):
        ref_table = {
            'vfio vfio_pci="1,2,3" module_blacklist="i915,kernel_module,kernel_module2,kernel_module3,kernel_module4" i915.modeset="0" mdev iommu="pt" intel_iommu="on" pcie_acs_override="downstream,multifunction,id:8086:1c4b,8086:0126,8086:0127" pcie_acs_override2="id:8086:1c4b"': [
                "vfio",
                {"vfio-pci": ["1", "2", "3"]},
                {"module-blacklist": ["i915", "kernel_module"]},
                {"module-blacklist": ["i915", "kernel_module2"]},
                {"module-blacklist": "kernel_module3"},
                {"module-blacklist": ["kernel_module4"]},
                {"module-blacklist": ["kernel_module3"]},
                {"i915.modeset": "0"},
                "mdev",
                {"iommu": "pt", "intel_iommu": "on"},
                {"pcie_acs_override": ["downstream", "multifunction", {"id": ["8086:1c4b", "8086:0126"]}]},
                {"pcie_acs_override": [{"id": ["8086:1c4b", "8086:0127"]}]},
                {"pcie_acs_override2": [{"id": ["8086:1c4b"]}]}
            ]
        }

        serializer = LinuxKernelParamsSerializer()
        for config_serialized, config in ref_table.items():
            result = serializer.serialize(config)
            self.assertEqual(result, config_serialized, f"\n\nRESULT\n{result}\n\nREF\n{config_serialized}")


class ShellConfig:
    __SPACE_SYMBOLS = "[\t ]"
    __SPACE_SYMBOLS_ZERO_OR_MORE = f"{__SPACE_SYMBOLS}*"
    __SPACE_SYMBOLS_ONE_OR_MORE = f"{__SPACE_SYMBOLS}+"

    __REGEX_NAME = r"([a-zA-Z_][a-zA-Z0-9_]*)"
    __REGEX = rf"^{RegexConstants.SPACE_SYMBOLS_ZERO_OR_MORE}({__REGEX_NAME}){RegexConstants.SPACE_SYMBOLS_ZERO_OR_MORE}={RegexConstants.SPACE_SYMBOLS_ZERO_OR_MORE}(.*)"
    __REGEX_STRING_DOUBLE_QUOTES = r"^\"(.*)\""
    __REGEX_STRING_SINGLE_QUOTES = r"^'(.*)'"

    def __init__(self, path):
        self.__reader = TextConfigReader(path)
        self.__writer = TextConfigWriter(path)
        self.__escape_literal = escape_literal
        self.__bool_from_string = bool_from_string
        self.__content = str()

    def get_value_as_is(self, parameter_name):
        print(parameter_name)

    def get_value_as_bool(self, parameter_name):
        print(parameter_name)

    def get_value_as_bool_or(self, parameter_name, default_value=False):
        print(parameter_name)

    def get_value_as_string(self, parameter_name):
        print(parameter_name)

    def get_value_as_int(self, parameter_name):
        print(parameter_name)

    def add_or_update(self):
        print("")

    def get_all(self):
        self.__load()
        regex = re.compile(self.__REGEX, re.MULTILINE)
        tmp = regex.findall(self.__content)

        result = dict()
        for name, value in tmp:
            result.update({name: FromString().get(value)})
        return result

    def __load(self):
        self.__content = self.__reader.get()

    def __save(self):
        self.__writer.set(self.__content)

    def __get_value(self, raw_string_value):
        if self.__is_bool(raw_string_value):
            return self.__bool_from_string.get(raw_string_value)
        else:
            return None

    def __is_bool(self, raw_string_value):
        return self.__bool_from_string.is_bool(raw_string_value)

    def __is_integer(self, raw_string_value):
        return raw_string_value.trim().isdigit()


class Power:
    # https://pythonassets.com/posts/shutdown-reboot-and-log-off-on-windows-and-linux/
    @staticmethod
    def reboot():
        if CurrentOs.is_linux():
            Logger.instance().warning("[Power] reboot!!!")
            Power.__reboot_linux()
        elif CurrentOs.is_windows():
            Logger.instance().warning("[Power] reboot!!!")
            Power.__reboot_windows()
        else:
            Logger.instance().warning("[Power] reboot not supported")

    @staticmethod
    def __reboot_linux():
        subprocess.check_call(["reboot"], shell=True)

    @staticmethod
    def __reboot_windows():
        subprocess.check_call(["shutdown", "/r", "/t", "0"], shell=True)


class Grub:
    GRUB_CMDLINE_LINUX = "GRUB_CMDLINE_LINUX"
    GRUB_TOP_LEVEL = "GRUB_TOP_LEVEL"

    def __init__(self, grub_config_backup_path=None, grub_config_file_path=Path("/etc/default/grub"),
                 boot_dir_path=Path("/boot")):
        self.__grub_config_reader = TextConfigReader(grub_config_file_path)
        self.__grub_config_writer = TextConfigWriter(grub_config_file_path,
                                                     last_backup_file_path=grub_config_backup_path)
        self.__boot_dir_path = Path(boot_dir_path)
        self.__linux_kernel_params_serializer = LinuxKernelParamsSerializer()
        self.__config_parser = ConfigParser()

    def update(self):
        Logger.instance().debug("[Grub] Update")
        subprocess.check_call(["update-grub"], shell=True)

    def append_cmd_line_linux(self, cmd_line_linux):
        grub_config = self.__grub_config_reader.get()

        grub_cmdline_linux = self.__config_parser.get_value(self.GRUB_CMDLINE_LINUX, grub_config)
        if grub_cmdline_linux is None:
            Logger.instance().warning(
                f"[Grub] {self.GRUB_CMDLINE_LINUX} parameter NOT FOUND in \"{self.__grub_config_reader}\":\n{grub_config}")
            grub_cmdline_linux = ""

        # fixme utopia Прибавляем новые аргументы простой конкатенацией, т.к. в общем случае в GRUB_CMDLINE_LINUX могут
        #  находиться переменные ($VAR / ${VAR}) или вычислимые выражения (`command substitution` / $(command substitution)),
        #  т.к. конфигурация grub представляет собой bash файл
        #  Пытаться делать объединение через разбор параметров GRUB_CMDLINE_LINUX считаю нецелесообразным
        separator = "" if len(grub_cmdline_linux) == 0 else " "
        new_linux_kernel_params_serialized = grub_cmdline_linux + separator + self.__linux_kernel_params_serializer.serialize(
            cmd_line_linux)

        grub_config_modified = self.__config_parser.add_or_update(self.GRUB_CMDLINE_LINUX,
                                                                  new_linux_kernel_params_serialized,
                                                                  grub_config)

        Logger.instance().debug(f"[Grub] Config before:\n{grub_config}\n\nConfig after:\n{grub_config_modified}\n")
        return self.__grub_config_writer.set_with_backup(grub_config_modified, is_rewrite_backup=True)

    def set_top_level(self, kernel_image_path):
        grub_config = self.__grub_config_reader.get()

        grub_config_modified = ""
        if kernel_image_path is None:
            grub_config_modified = self.__config_parser.remove_by_name(self.GRUB_TOP_LEVEL, grub_config)
        else:
            grub_config_modified = self.__config_parser.add_or_update(self.GRUB_TOP_LEVEL,
                                                                      str(kernel_image_path),
                                                                      grub_config)

        Logger.instance().debug(f"[Grub] Config before:\n{grub_config}\n\nConfig after:\n{grub_config_modified}\n")
        return self.__grub_config_writer.set_with_backup(grub_config_modified, is_rewrite_backup=True)

    def restore_from_backup(self):
        Logger.instance().debug(
            f"[Grub] Restore from backup \"{self.__grub_config_writer.get_last_backup_file_path()}\"")
        return self.__grub_config_writer.restore_from_backup(is_remove_backup=True)

    def get_last_liquorix_kernel_path(self):
        return self.__get_last_kernel_path(is_liquorix=True)

    def get_last_normal_kernel_path(self):
        return self.__get_last_kernel_path(is_liquorix=False)

    def __get_last_kernel_path(self, is_liquorix):
        for path in sorted(pathlib.Path(str(self.__boot_dir_path)).glob("vmlinuz-*"),
                           key=lambda x: LinuxKernelVersion(str(x)), reverse=True):
            if path.is_file():
                current_kernel_is_liqourix = LinuxKernelVersion(str(path)).is_liquorix()
                if is_liquorix and current_kernel_is_liqourix:
                    return Path(str(path))
                elif not is_liquorix and not current_kernel_is_liqourix:
                    return Path(str(path))
        return None


class AsyncRunner:
    STDOUT_DECODE = "UTF8"
    STDERR_DECODE = STDOUT_DECODE

    def __init__(self):
        self.__runnable_descriptor_list_parallel = []
        self.__runnable_descriptor_list_sequential = []

    def add(self, script_path_or_command, is_background_executing=False, shell=True):
        if bool(is_background_executing):
            self.__runnable_descriptor_list_parallel.append((script_path_or_command, shell))
        else:
            self.__runnable_descriptor_list_sequential.append((script_path_or_command, shell))

    async def run_all(self):
        runnable_list = [
            self.__run_sequential(*self.__runnable_descriptor_list_sequential,
                                  handler=lambda x: self.__run(x)),
            self.__run_parallel(*self.__runnable_descriptor_list_parallel,
                                handler=lambda x: self.__run(x))]

        result = await self.__run_parallel(*runnable_list)
        return result[0] + result[1]

    async def __run(self, runnable_descriptor):
        script_path_or_command, shell = runnable_descriptor

        Logger.instance().debug(f'[ScriptRun] Start "{script_path_or_command}"')

        if shell:
            process = await asyncio.create_subprocess_shell(str(script_path_or_command), stdout=asyncio.subprocess.PIPE,
                                                            stderr=asyncio.subprocess.PIPE)
        else:
            command_with_args = shlex.split(str(script_path_or_command))
            if not command_with_args:
                raise Exception(f'[ScriptRun] Command IS EMPTY: "{script_path_or_command}"')
            command = command_with_args[0]
            args = command_with_args[1:]
            process = await asyncio.create_subprocess_exec(command, *args, stdout=asyncio.subprocess.PIPE,
                                                           stderr=asyncio.subprocess.PIPE)
        pid = process.pid
        try:
            Logger.instance().debug(f'[ScriptRun] Started [pid={pid}] "{script_path_or_command}"')
            await self.__run_parallel(self.__log_stdout(process.stdout), self.__log_stderr(process.stderr))
            return await self.__wait(process, script_path_or_command)
        except asyncio.CancelledError:
            process.kill()
            Logger.instance().debug(f'[ScriptRun] KILL [pid={pid}] "{script_path_or_command}"')
            return await self.__wait(process, script_path_or_command)

    async def __wait(self, process, script_path_or_command):
        await process.wait()
        Logger.instance().debug(
            f'[ScriptRun] End [pid={process.pid}, exit_code={process.returncode}] "{script_path_or_command}"')
        return process.pid, process.returncode

    async def __run_parallel(self, *task_list, handler=None):
        return await asyncio.gather(*self.__prepare_task_list(*task_list, handler=handler), return_exceptions=True)

    async def __run_sequential(self, *task_list, handler=None):
        result = []
        for task in self.__prepare_task_list(*task_list, handler=handler):
            try:
                result.append(await task)
            except Exception as ex:
                result.append(ex)
        return result

    def __prepare_task_list(self, *task_list, handler=None):
        result = []
        for task in task_list:
            if isinstance(task, list):
                result.extend(self.__prepare_task_list(*task, handler=handler))
                continue

            if handler is not None:
                task = handler(task)
            if task is None or isinstance(task, Exception):
                task = self.__pass_value(task)

            result.append(task)
        return result

    async def __pass_value(self, val):
        return val

    async def __log_stdout(self, stdout_stream):
        while True:
            buffer = await stdout_stream.readline()
            if buffer:
                Logger.instance().debug(buffer.decode(self.STDOUT_DECODE))
            else:
                break

    async def __log_stderr(self, stderr_stream):
        while True:
            buffer = await stderr_stream.readline()
            if buffer:
                Logger.instance().error(buffer.decode(self.STDERR_DECODE))
            else:
                break


class UnitTest_AsyncRunner(unittest.TestCase):
    __EXIT_CODE = 55
    __SHELL_EXIT_CODE_COMMAND_NOT_FOUND_IN_THE_SYSTEMS_PATH = 127

    def test(self):
        asyncio.run(self.__run_success())
        asyncio.run(self.__run_non_existing_script())

    async def __run_success(self):
        async_script_runner = AsyncRunner()
        script1 = TextConfigWriter("test_data/script1.sh")

        test_script = f"""echo "message 0"
sleep 1

echo "message 1"
sleep 1

echo "message 2"

exit {self.__EXIT_CODE}   
"""
        script1.set(test_script)
        async_script_runner.add(str(script1))
        result = await async_script_runner.run_all()
        pid, exit_code = result[0]
        self.assertEqual(exit_code, self.__EXIT_CODE)

    async def __run_non_existing_script(self):
        async_script_runner = AsyncRunner()
        async_script_runner.add(Path("non_exist_script.sh"))
        result = await async_script_runner.run_all()
        pid, exit_code = result[0]
        self.assertEqual(exit_code, self.__SHELL_EXIT_CODE_COMMAND_NOT_FOUND_IN_THE_SYSTEMS_PATH)


class StartupCrontab:
    COMMAND = "startup_run_all_scripts"
    SUPERVISOR_SCRIPT_ID = "073c0542-ab8f-4518-802b-4417a4519219"

    __STARTUP_SCRIPTS_DIR_NAME = ".crontab_startup_scripts"
    __RUN_ONCE_SCRIPT_DIR_NAME = "run_once"

    class StartupScriptName:
        __ENCODE = "utf-8"
        __NAME = "name"
        __IS_BACKGROUND_EXECUTING_LABEL = "_bg"
        __IS_BACKGROUND_EXECUTING = "is_background_executing"
        __IS_EXECUTE_ONCE_LABEL = "_once"
        __IS_EXECUTE_ONCE = "is_execute_once"

        __EXTENSION = ".sh"

        __REGEX_MD5 = "[a-f0-9]{32}"
        __REGEX = f"(?P<{__NAME}>{__REGEX_MD5})(?P<{__IS_BACKGROUND_EXECUTING}>{__IS_BACKGROUND_EXECUTING_LABEL})?(?P<{__IS_EXECUTE_ONCE}>{__IS_EXECUTE_ONCE_LABEL})?\\{__EXTENSION}"

        def __init__(self, is_background_executing, is_execute_once, startup_script_content, name=None):
            self.is_background_executing = is_background_executing
            self.is_execute_once = is_execute_once
            self.name = name if isinstance(name, str) else self.__get_startup_script_name_by_content(
                startup_script_content)

        def __str__(self):
            return self.get()

        def __repr__(self):
            return self.__str__()

        def get(self):
            return f"{self.name}{self.__get_background_executing_prefix()}{self.__get_execute_once_prefix()}{self.__EXTENSION}"

        def get_wildcard(self):
            return f"{self.name}*{self.__EXTENSION}"

        def __get_startup_script_name_by_content(self, startup_script_content):
            return hashlib.md5(str(startup_script_content).encode(self.__ENCODE)).hexdigest()

        def __get_background_executing_prefix(self):
            return self.__IS_BACKGROUND_EXECUTING_LABEL if self.is_background_executing else ""

        def __get_execute_once_prefix(self):
            return self.__IS_EXECUTE_ONCE_LABEL if self.is_execute_once else ""

        @staticmethod
        def parse(startup_script_file_name):
            regex = re.compile(StartupCrontab.StartupScriptName.__REGEX)
            match = regex.fullmatch(startup_script_file_name)
            if match is None:
                return None

            name = match.group(StartupCrontab.StartupScriptName.__NAME)
            is_background_executing = bool(match.group(StartupCrontab.StartupScriptName.__IS_BACKGROUND_EXECUTING))
            is_execute_once = bool(match.group(StartupCrontab.StartupScriptName.__IS_EXECUTE_ONCE))

            return StartupCrontab.StartupScriptName(is_background_executing=is_background_executing,
                                                    is_execute_once=is_execute_once, startup_script_content=None,
                                                    name=name)

    def __init__(self, user=getpass.getuser()):
        self.__user = user

    def register_script(self, startup_script_content, is_background_executing=False,
                        is_execute_once=False):
        self.__register_supervisor_script()
        startup_script_name = StartupCrontab.StartupScriptName(is_background_executing=is_background_executing,
                                                               is_execute_once=is_execute_once,
                                                               startup_script_content=startup_script_content)
        return self.__create_startup_script_file(startup_script_name, startup_script_content)

    def run_all_scripts(self):
        self.__remake_execute_once_script_dir()
        script_runner = AsyncRunner()
        for path in sorted(pathlib.Path(self.__get_startup_script_dir_path().get()).glob("*"),
                           key=lambda x: x.stat().st_mtime_ns, reverse=True):
            if path.is_file():
                startup_script_name = StartupCrontab.StartupScriptName.parse(path.name)
                if startup_script_name is not None:
                    if startup_script_name.is_execute_once:
                        path = path.replace(self.__get_execute_once_script_dir_path() / path.name)
                    script_runner.add(path, startup_script_name.is_background_executing)
        asyncio.run(script_runner.run_all())
        self.__remove_execute_once_script_dir()

    def __remake_execute_once_script_dir(self):
        self.__remove_execute_once_script_dir()
        self.__get_execute_once_script_dir_path().mkdir(parents=True, exist_ok=True)

    def __remove_execute_once_script_dir(self):
        shutil.rmtree(self.__get_execute_once_script_dir_path(), ignore_errors=True)

    def __register_supervisor_script(self):
        with CronTab(user=self.__user) as cron:
            command = f'"{sys.executable}" "{__file__}" {self.COMMAND}'
            if next(cron.find_comment(self.SUPERVISOR_SCRIPT_ID), None) is not None:
                return

            Logger.instance().debug(f"[Startup] Register supervisor script: {command}")
            job = cron.new(command=command, comment=self.SUPERVISOR_SCRIPT_ID)
            job.every_reboot()

    def __create_startup_script_file(self, startup_script_name, startup_script_content):
        startup_script_file_path = self.__get_startup_script_file_path(startup_script_name)
        if self.__is_startup_script_file_exists(startup_script_name):
            Logger.instance().debug(f"[Startup] Script \"{startup_script_file_path}\" ALREADY EXISTS")
            return False

        Logger.instance().debug(f"[Startup] Create script \"{startup_script_file_path}\":\n{startup_script_content}\n")
        TextConfigWriter(startup_script_file_path).set(startup_script_content, set_executable=True)
        return True

    def __get_startup_script_file_path(self, startup_script_name):
        return self.__get_startup_script_dir_path().join(startup_script_name.get())

    def __is_startup_script_file_exists(self, startup_script_name):
        return self.__get_startup_script_dir_path().exists_by_wildcard(startup_script_name.get_wildcard())

    def __get_execute_once_script_dir_path(self):
        return pathlib.Path(str(self.__get_startup_script_dir_path())) / self.__RUN_ONCE_SCRIPT_DIR_NAME

    def __get_startup_script_dir_path(self):
        return Path.get_home_directory(self.__user).join(self.__STARTUP_SCRIPTS_DIR_NAME)


# Windows startup
# https://superuser.com/a/1518663/2121020
# fixme utopia Переопределить метод __register_supervisor_script()
class StartupWindows(StartupCrontab):
    pass


class Startup:
    def __init__(self, user=getpass.getuser()):
        if CurrentOs.is_linux():
            self.__startup_impl = StartupCrontab(user)
        elif CurrentOs.is_windows() or CurrentOs.is_msys():
            # self.__startup_impl = StartupWindows()
            raise Exception("[Startup] NOT IMPLEMENTED")
        else:
            raise Exception("[Startup] NOT IMPLEMENTED")

    def register_script(self, startup_script_content, is_background_executing=False,
                        is_execute_once=False):
        return self.__startup_impl.register_script(startup_script_content=startup_script_content,
                                                   is_background_executing=is_background_executing,
                                                   is_execute_once=is_execute_once)

    def run_all_scripts(self):
        self.__startup_impl.run_all_scripts()


# https://qemu-project.gitlab.io/qemu/specs/tpm.html
# https://en.opensuse.org/Software_TPM_Emulator_For_QEMU
# https://www.qemu.org/docs/master/system/invocation.html#hxtool-7
class TpmEmulator(DaemonManagerBase):
    PREFIX = "swtpm"
    TPM_CMD = "swtpm"
    TPM_DEVICE_DEFAULT = "tpm-tis"

    class TpmSerializer(ShellSerializer):
        class TpmEscapeLiteral(EscapeLiteral):
            def __init__(self):
                super().__init__(encode_table=[(",", ",,")])

        def __init__(self):
            super().__init__(key_value_separator_table=[
                {"prefix": "", "separator": " "}], quotes_for_string_value="", nested_serializer=ShellSerializer(
                key_value_separator_table=[
                    {"prefix": "",
                     "separator": " "}],
                pair_separator=" ",
                escape_literal=QemuSerializer.QemuEscapeLiteral(),
                nested_serializer=ShellSerializer(
                    quotes_for_string_value="",
                    key_value_separator_table=[
                        {"prefix": "",
                         "separator": "="}],
                    pair_separator=",",
                    escape_literal=QemuSerializer.QemuEscapeLiteral()),
                nested_key_value_separator=" "
            ))

    def __init__(self, vm_meta_data, is_tpm2_0=True, log_level=20):
        super().__init__(label="TpmEmulator", action="Start")
        self.__vm_meta_data = vm_meta_data
        self.__is_tpm2_0 = is_tpm2_0
        self.__log_level = log_level
        self.__serializer = TpmEmulator.TpmSerializer()

    def get_qemu_parameters(self):
        self.__get_tpm_state_dir_path().mkdir(parents=True, exist_ok=True)
        return [{"-chardev": {"socket": {"id": self.__get_tpm_chardev_id(),
                                         "path": self.__get_tpm_chardev_ctrl_unixsocket_path()}}},
                {"-tpmdev": {
                    "emulator": {"id": self.__get_tpm_dev_id(), "chardev": self.__get_tpm_chardev_id()}}},

                {"-device": {
                    self.__get_tpm_dev_model(): {"tpmdev": self.__get_tpm_dev_id()}}}
                ]

    def _start_impl(self):
        self.__get_tpm_state_dir_path().mkdir(parents=True, exist_ok=True)

    def _close_impl(self):
        return

    def _build_command_line(self):
        return f"{self.TPM_CMD} {self.__serializer.serialize(self.__get_command_line_args())}"

    def __get_command_line_args(self):
        return {"socket": [{"--tpmstate": {"dir": self.__get_tpm_state_dir_path()}},
                           {"--ctrl": {"type": "unixio", "path": self.__get_tpm_chardev_ctrl_unixsocket_path()}},
                           "--tpm2" if self.__is_tpm2_0 else "",
                           {"--log": {"level": self.__log_level, "file": self.__get_tpm_log_file_path()}},
                           "--daemon"]}

    def __get_tpm_chardev_id(self):
        return f"{self.PREFIX}-{self.__vm_meta_data.get_name()}-chardev-id"

    def __get_tpm_chardev_ctrl_unixsocket_path(self):
        return self.__get_tpm_state_dir_path() / self.__get_tpm_chardev_ctrl_unixsocket_name()

    def __get_tpm_log_file_path(self):
        return self.__get_tpm_state_dir_path() / f"{self.PREFIX}.log"

    def __get_tpm_state_dir_path(self):
        return self.__vm_meta_data.get_working_dir_path() / self.PREFIX

    def __get_tpm_chardev_ctrl_unixsocket_name(self):
        return f"{self.PREFIX}-sock"

    def __get_tpm_dev_model(self):
        # fixme utopia tpm-tis / tpm-spapr / tpm-tis-device / tpm-tis-i2c
        return self.TPM_DEVICE_DEFAULT

    def __get_tpm_dev_id(self):
        return f"{self.PREFIX}-{self.__vm_meta_data.get_name()}-dev-id"


# https://superuser.com/a/1412150/2121020
class QemuSerial:
    PREFIX = "serial"

    __index = -1

    def __init__(self, vm_meta_data):
        QemuSerial.__index += 1
        self.__vm_meta_data = vm_meta_data

    def get_qemu_parameters(self):
        self.__get_serial_state_dir_path().mkdir(parents=True, exist_ok=True)
        return [{"-chardev": {
            "file": {"id": self.__get_serial_chardev_id(), "mux": "on", "path": self.__get_serial_log_file_path(),
                     "signal": "off"}}}, {"-serial": f"chardev:{self.__get_serial_chardev_id()}"}]

    def __get_serial_chardev_id(self):
        return f"{self.PREFIX}-{self.__vm_meta_data.get_name()}-chardev-id{self.__index}"

    def __get_serial_log_file_path(self):
        return self.__get_serial_state_dir_path() / f"{self.PREFIX}.log"

    def __get_serial_state_dir_path(self):
        return self.__vm_meta_data.get_working_dir_path() / f"{self.PREFIX}{self.__index}"


class QemuLogging:
    PREFIX = "qemu"

    def __init__(self, vm_meta_data):
        self.__vm_meta_data = vm_meta_data

    def get_qemu_parameters(self):
        self.__get_qemu_state_dir_path().mkdir(parents=True, exist_ok=True)
        return [{"-D": self.__get_qemu_log_file_path()}]

    def __get_qemu_log_file_path(self):
        return self.__get_qemu_state_dir_path() / f"{self.PREFIX}.log"

    def __get_qemu_state_dir_path(self):
        return self.__vm_meta_data.get_working_dir_path() / self.PREFIX


# https://github.com/tianocore/edk2/blob/master/OvmfPkg/README
# https://superuser.com/a/1798353/2121020
# https://www.qemu.org/docs/master/system/invocation.html#hxtool-0
class QemuUefi:
    PREFIX = "uefi"
    OVMF_CODE_SECURE_BOOT = "OVMF_CODE_4M.secboot.fd"
    OVMF_CODE_BOOT = "OVMF_CODE_4M.fd"
    OVMF_VARS = "OVMF_VARS_4M.ms.fd"

    def __init__(self, vm_meta_data, ovmf_dir_path=Path("/usr/share/OVMF"), is_secure_boot=True):
        self.__vm_meta_data = vm_meta_data
        self.__ovmf_dir_path = Path(str(ovmf_dir_path))
        self.__is_secure_boot = is_secure_boot

    def get_qemu_parameters(self):
        if not self.__get_vm_ovmf_vars_file_path().exists():
            self.__get_uefi_state_dir_path().makedirs()
            self.__get_vm_ovmf_vars_file_path().copy_from(self.__get_ovmf_vars_file_path())
        return [
            {"-machine": "q35"},
            {"-drive": {
                "if": "pflash", "format": "raw", "file": self.__get_ovmf_code_file_path(), "readonly": "on"}},
            {"-drive": {
                "if": "pflash", "format": "raw", "file": self.__get_vm_ovmf_vars_file_path()}}]

    def __get_ovmf_code_file_path(self):
        if self.__is_secure_boot:
            return self.__ovmf_dir_path.join(self.OVMF_CODE_SECURE_BOOT)
        else:
            return self.__ovmf_dir_path.join(self.OVMF_CODE_BOOT)

    def __get_ovmf_vars_file_path(self):
        return self.__ovmf_dir_path.join(self.OVMF_VARS)

    def __get_vm_ovmf_vars_file_path(self):
        return self.__get_uefi_state_dir_path().join(self.OVMF_VARS)

    def __get_uefi_state_dir_path(self):
        return Path(self.__vm_meta_data.get_working_dir_path()).join(self.PREFIX)


class QemuBios:
    def __init__(self, vm_meta_data, chipset=None):
        self.__vm_meta_data = vm_meta_data
        self.__chipset = chipset

    # SeaBIOS используется по умолчанию, дополнительные аргументы не требуются
    def get_qemu_parameters(self):
        # https://www.seabios.org/Debugging
        # https://forums.gentoo.org/viewtopic-p-8812362.html?sid=f8b324e3711f9796b6a777e198212a6d
        result = [{"-chardev": {"file": {"path": self.__get_log_file_path(), "id": "seabios"}}, "-device": {
            "isa-debugcon": {"iobase": 0x402, "chardev": "seabios"}}}]
        if self.__chipset is not None:
            result.append({"-machine": self.__chipset})
        return result

    def __get_log_file_path(self):
        return self.__vm_meta_data.get_working_dir_path() / "seabios.log"


# https://www.qemu.org/docs/master/system/devices/virtio-gpu.html
# https://www.qemu.org/docs/master/system/invocation.html#hxtool-3
# https://wiki.archlinux.org/title/QEMU#virtio
# https://wiki.archlinux.org/title/QEMU/Guest_graphics_acceleration#Virgil3d_virtio-gpu_paravirtualized_device_driver
# https://github.com/virtio-win/kvm-guest-drivers-windows/pull/943
# Полноценно работает только для Linux guest, для Windows guest отсутствуют драйвера для virtio-gpu
class QemuVgaVirtio:
    def __init__(self):
        pass

    def get_qemu_parameters(self):
        return [{"-device": "virtio-vga-gl", "-display": {"sdl": {"gl": "on"}}}]


class QemuVgaDefault:
    def __init__(self):
        pass

    def get_qemu_parameters(self):
        return [{"-vga": "std", "-display": {"gtk": {}}}]


class QemuPciPassthrough:
    def __init__(self, vfio_pci):
        if isinstance(vfio_pci, VfioPci):
            self.__vfio_pci = vfio_pci
        elif isinstance(vfio_pci, str):
            self.__vfio_pci = VfioPci.from_string(vfio_pci)
        else:
            raise Exception(f"[QemuPciPassthrough] vfio_pci TYPE MISMATCH: {type(vfio_pci)}")

    def __str__(self):
        return str(self.__vfio_pci)

    def __repr__(self):
        return self.__str__()

    def get_qemu_parameters(self, vm_meta_data):
        return self.__vfio_pci.get_qemu_parameters(vm_meta_data)

    def is_other_vga_disable(self):
        return self.__vfio_pci.is_other_vga_disable()

    def check_platform(self, qemu_platform):
        return self.__vfio_pci.check_platform(qemu_platform)


# fixme utopia Обеспечить возможность установки win11
# https://serverfault.com/a/1096401/1120954
# https://extralan.ru/?p=3060
# secure-boot check win11
# https://www.iobit.com/en/knowledge-how-to-enable-secure-boot-on-windows--355.php
# - TPM (software)
# - UEFI (OVMF) + secure boot
# - 4 GB RAM
# - CPU Icelake-Server-v5
class VirtualMachine:
    def __init__(self, network_bridge,
                 vm_meta_data,
                 qemu_serial=None, qemu_logging=None,
                 qemu_platform=None, qemu_vga=None, qemu_pci_passthrough=None, qemu_cdrom=QemuCdRom(),
                 qemu_builtin_kbd_and_mouse_passthrough=None):
        self.__tap = Tap()
        self.__network_bridge = network_bridge
        self.__vm_meta_data = vm_meta_data
        self.__qemu_serial = QemuSerial(vm_meta_data) if qemu_serial is None else qemu_serial
        self.__qemu_logging = QemuLogging(vm_meta_data) if qemu_logging is None else qemu_logging
        self.__qemu_platform = QemuPlatform(vm_meta_data) if qemu_platform is None else qemu_platform
        self.__qemu_vga = QemuVgaDefault() if qemu_vga is None else qemu_vga
        self.__qemu_pci_passthrough = qemu_pci_passthrough
        self.__qemu_cdrom = QemuCdRom() if qemu_cdrom is None else qemu_cdrom
        self.__qemu_builtin_kbd_and_mouse_passthrough = qemu_builtin_kbd_and_mouse_passthrough
        self.__serializer = QemuSerializer()

    def run(self):
        self.__network_bridge.create()
        self.__qemu_platform.before_start_vm()

        command_line = self.__command_line()
        Logger.instance().debug(f"[Vm] Run cmd: {command_line}")
        result = subprocess.run(command_line, shell=True, capture_output=True, text=True)
        Logger.instance().debug(f"[Vm] Run result:\nSTDOUT\n{result.stdout}\nSTDERR\n{result.stderr}\n")

        self.__qemu_platform.after_stop_vm()

    def __command_line(self):
        command_parts_list = [self.__qemu_command_line(),
                              self.__get_qemu_platform_command_line(),
                              self.__kvm_enable(),
                              self.__ram_size(),
                              self.__network(),
                              self.__other(),
                              self.__disk(),
                              self.__cpu(),
                              self.__get_qemu_vga_command_line(),
                              self.__qemu_pci_passthrough_command_line(),
                              self.__usb(),
                              self.__monitor(),
                              self.__get_qemu_serial_command_line(),
                              self.__get_qemu_logging_command_line(),
                              self.__get_qemu_cdrom_command_line(),
                              self.__get_qemu_builtin_kbd_and_mouse_passthrough_command_line()
                              ]
        return " ".join(command_parts_list)

    @staticmethod
    def __qemu_command_line():
        # return str(Path(".").join("qemu").join("build").join(f"qemu-system-{platform.machine()}"))
        return "qemu-system-{}".format(platform.machine())

    @staticmethod
    def __kvm_enable():
        if CurrentOs.is_linux():
            return "-accel kvm"
        elif CurrentOs.is_msys():
            return "-accel whpx"
        else:
            return "-accel tcg"

    @staticmethod
    def __ram_size():  # fixme utopia Использовать psutil
        return "-m 8000"

    def __network(self):
        self.__tap.create()
        self.__network_bridge.add_and_configure_tap(self.__tap, self.__vm_meta_data)

        tap_name = str(self.__tap)
        netdev_id = "{}-id".format(tap_name)

        # fixme utopia Присвоим ip адрес vm через mac адрес
        # https://superuser.com/questions/1413011/setting-a-static-ip-upon-qemu-vm-creation

        return "-netdev tap,ifname={0},script=no,downscript=no,id={1} -device virtio-net,netdev={1},mac={2},addr=0x3".format(
            tap_name, netdev_id, self.__vm_meta_data.get_mac_address_as_string())

    def __disk(self):
        return "-drive file=\"{}\",media=disk,if=virtio".format(self.__vm_meta_data.get_image_path())

    def __other(self):
        # -bt hci,host:hci0
        # https://qemu-project.gitlab.io/qemu/system/devices/usb.html
        # https://www.youtube.com/watch?v=ELbxhm1-rno
        # -full-screen
        # return "-vnc 127.0.0.1:2 -soundhw hda"
        return '-vnc 127.0.0.1:2'

    def __monitor(self):
        # fixme utopia config monitor port
        # https://unix.stackexchange.com/questions/426652/connect-to-running-qemu-instance-with-qemu-monitor
        return "-monitor telnet:127.0.0.1:55555,server,nowait"

    def __cpu(self):
        # CPU который поддерживается Windows 11 Icelake-Server-v5
        return "-cpu host -smp 4,sockets=1,cores=2,threads=2,maxcpus=4"

    def __usb(self):
        usb_device_array = [
            (0x045e, 0x00db),  # Клавиатура Microsoft # Natural Ergonomic Keyboard 4000 v 1.0
            (0x0bda, 0x8771),  # USB-Bluetooth 5.0 адаптер Ugreen # CM390
            (0x046d, 0xc05b),  # Мышка Logitec # B110
            (0x258a, 0x0302)  # Клавиатура с тачпадом Harper # KBT-330
        ]

        result = []

        for vid, pid in usb_device_array:
            result.append("-usb -device usb-host,vendorid=0x{:04X},productid=0x{:04X}".format(vid, pid))

        return " ".join(result)

    def __get_qemu_platform_command_line(self):
        if self.__qemu_platform is None:
            return ""
        return self.__serializer.serialize(self.__qemu_platform.get_qemu_parameters())

    def __get_qemu_vga_command_line(self):
        if self.__qemu_pci_passthrough is not None and self.__qemu_pci_passthrough.is_other_vga_disable():
            return ""
        return self.__serializer.serialize(self.__qemu_vga.get_qemu_parameters())

    def __qemu_pci_passthrough_command_line(self):
        if self.__qemu_pci_passthrough is None:
            return ""
        self.__qemu_pci_passthrough.check_platform(self.__qemu_platform)
        return self.__serializer.serialize(self.__qemu_pci_passthrough.get_qemu_parameters(self.__vm_meta_data))

    def __get_qemu_serial_command_line(self):
        return ""  # self.__serializer.serialize(self.__qemu_serial.get_qemu_parameters())

    def __get_qemu_logging_command_line(self):
        return ""  # self.__serializer.serialize(self.__qemu_logging.get_qemu_parameters())

    def __get_qemu_cdrom_command_line(self):
        if self.__qemu_cdrom is None:
            return ""
        return self.__serializer.serialize(self.__qemu_cdrom.get_qemu_parameters())

    def __get_qemu_builtin_kbd_and_mouse_passthrough_command_line(self):
        if self.__qemu_builtin_kbd_and_mouse_passthrough is None:
            return ""
        return self.__serializer.serialize(self.__qemu_builtin_kbd_and_mouse_passthrough.get_qemu_parameters())


class VmRunner:
    def __init__(self, vm_name, project_config=OpenVpnConfig(), startup=Startup(), block_internet_access=False,
                 initiate_vga_passthrough=False,
                 initiate_vga_audio_passthrough=False,
                 initiate_usb_host_passthrough=False,
                 initiate_isa_bridge_passthrough=False,
                 initiate_builtin_kbd_and_mouse_passthrough=False,
                 asc_override_patched_kernel=False,
                 qemu_pci_passthrough=None, grub_config_backup_path=None,
                 vm_platform=None, os_distr_path=None):
        self.__vm_name = vm_name
        self.__project_config = project_config
        self.__startup = startup
        self.__block_internet_access = bool(block_internet_access)
        self.__initiate_vga_passthrough = bool(initiate_vga_passthrough)
        self.__initiate_vga_audio_passthrough = bool(initiate_vga_audio_passthrough)
        self.__initiate_usb_host_passthrough = bool(initiate_usb_host_passthrough)
        self.__initiate_isa_bridge_passthrough = bool(initiate_isa_bridge_passthrough)
        self.__initiate_builtin_kbd_and_mouse_passthrough = bool(initiate_builtin_kbd_and_mouse_passthrough)
        self.__asc_override_patched_kernel = bool(asc_override_patched_kernel)
        self.__qemu_pci_passthrough = qemu_pci_passthrough
        self.__vm_platform = vm_platform
        self.__os_distr_path = os_distr_path
        self.__grub = Grub(grub_config_backup_path=grub_config_backup_path)
        self.__serializer = ShellSerializer()

    def run(self):
        if self.__initiate_vga_passthrough or self.__initiate_usb_host_passthrough or self.__initiate_isa_bridge_passthrough:
            if self.__qemu_pci_passthrough:
                self.after_reboot()
            else:
                self.before_reboot()
        else:
            self.__run()

    def before_reboot(self):
        pci_list = Pci.get_list()
        if not pci_list.is_iommu_enabled():
            Logger.instance().warning(
                "[Vm] Enable IOMMU (VT-d/AMD-Vi) in host BIOS/UEFI.\n     See guide https://us.informatiweb.net/tutorials/it/bios/enable-iommu-or-vt-d-in-your-bios.html")

            grub_config_backup_path = self.__grub.append_cmd_line_linux(
                Vfio(VfioPci(Pci.PciList())).get_kernel_parameters())
            if grub_config_backup_path is None:
                Logger.instance().error("[Vm] Make GRUB config backup FAIL")
                return
            self.__grub.update()
            Logger.instance().info(
                f"[Vm] GRUB config for IOMMU applied\n     GRUB backup: \"{grub_config_backup_path}\"")
            return

        pci_list_for_passthrough = Pci.PciList()
        pci_list_for_passthrough.extend(self.__get_pci_vga_list_for_passthrough(pci_list))
        pci_list_for_passthrough.extend(self.__get_usb_host_list_for_passthrough(pci_list))
        pci_list_for_passthrough.extend(self.__get_isa_bridge_list_for_passthrough(pci_list))

        if len(pci_list_for_passthrough) == 0:
            Logger.instance().warning("[Vm] PCI passthrough devices NOT FOUND")
            return

        check_iommu_group_for_passthrough = pci_list.check_iommu_group_for_passthrough(pci_list_for_passthrough)
        if check_iommu_group_for_passthrough is False:
            if self.__asc_override_patched_kernel:
                Logger.instance().warning("[Vm] Add ASC override patched kernel")
                LinuxKernel().download_and_install_liquorix_kernel()
                # Параметр GRUB_TOP_LEVEL доступен начиная с GRUB 2.12
                # После завершения работы виртуальной машины ядро не откатываем.
                # Пользователь может самостоятельно или удалить liquorix ядро (пакет) или воспользоваться grub-customizer
                # Если бы откат на предыдущее ядро после выключения виртуальной машины был доступен, то пришлось бы решать следующие проблемы:
                # 1. установка GRUB_TOP_LEVEL на предыдущее ядро блокирует использование обновленного умолчательного ядра
                # 2. удаление liquorix ядра (а соответственно и правильный автоматический откат на умолчательное ядро) приводит постоянному скачиванию и установке liquorix ядра
                #    - это лишний интернет трафик
                # 3. если GRUB не чувствителен к GRUB_TOP_LEVEL, то liquorix ядро может не примениться из-за того что это ядро по версии меньше последнего умолчательного
                # 4. при использовании GRUB_TOP_LEVEL на liquorix ядро GRUB будет не чувствителен к обновлениям этого ядра
                # 5. установка GRUB_DEFAULT и/или GRUB_TOP_LEVEL мешает обновлению ядер, например, параметры указывают на удалённое ядро
                # 6. может быть единственно правильный вариант: скачивать liquorix ядро в виде deb пакета (apt download), устанавливать перед запуском виртуальной машины и удалять после
                #    (придётся решать проблему поиска последней версии liquorix ядра вручную)
                # 6.1 или пересборка текущего умолчательного ядра с ASC override патчем
                # self.__grub.set_top_level(self.__grub.get_last_liquorix_kernel_path())
                grub_config_backup_path = self.__grub.append_cmd_line_linux(
                    Vfio(VfioPci(Pci.PciList())).get_kernel_parameters())
                if grub_config_backup_path is None:
                    Logger.instance().error("[Vm] Make GRUB config backup FAIL")
                    return
                self.__grub.update()
                Logger.instance().warning(f"[Vm] Reboot PC and retry\n     GRUB backup: {grub_config_backup_path}")
            else:
                Logger.instance().warning(
                    "[Vm] For PCI passthrough require ASC override patched kernel.\n     Add --asc_override_patched_kernel parameter and retry")
            return
        elif check_iommu_group_for_passthrough is None:
            return

        vfio_pci = VfioPci(pci_list_for_passthrough)
        vfio = Vfio(vfio_pci)

        grub_config_backup_path = self.__grub.append_cmd_line_linux(vfio.get_kernel_parameters())
        if grub_config_backup_path is None:
            Logger.instance().error("[Vm] Make GRUB config backup FAIL")
            return
        self.__grub.update()

        args = [self.__vm_name, "--bi" if self.__block_internet_access else "",
                {"--qemu_pci_passthrough": str(QemuPciPassthrough(vfio_pci)),
                 "--grub_config_backup_path": str(grub_config_backup_path)},
                "--vga_passthrough" if self.__initiate_vga_passthrough else "",
                "--usb_host_passthrough" if self.__initiate_usb_host_passthrough else "",
                "--isa_bridge_passthrough" if self.__initiate_isa_bridge_passthrough else "",
                "--builtin_kbd_and_mouse_passthrough" if self.__initiate_builtin_kbd_and_mouse_passthrough else ""]

        command_line = f'"{sys.executable}" "{__file__}" {self.__serializer.serialize(["vm_run", args])}'

        self.__startup.register_script(command_line, is_background_executing=True, is_execute_once=True)
        Power.reboot()

    def after_reboot(self):
        sleep_sec = 30
        # Требуется для инициализации сетевой инфраструктуры (WiFi) иначе vm не стартанёт
        Logger.instance().debug(f"[Vm] Sleep {sleep_sec} before vm run")
        time.sleep(sleep_sec)
        dmesg_output = subprocess.run("dmesg", shell=True, capture_output=True, text=True)
        Logger.instance().debug(f"[Vm] dmesg:\n{dmesg_output.stdout}\n")
        Logger.instance().debug(f"[Vm] PCI device list:\n{Pci.get_list()}\n")

        for i in range(1):
            try:
                self.__run()
            except Exception as ex:
                Logger.instance().exception(f"[Vm] {i} Run after reboot FAIL")

        self.__grub.restore_from_backup()
        self.__grub.update()
        Power.reboot()

    def __get_pci_vga_list_for_passthrough(self, pci_list):
        if not self.__initiate_vga_passthrough:
            return Pci.PciList()

        # VGA + Audio controller
        result = pci_list.get_vga_list(with_consumer=self.__initiate_vga_audio_passthrough)
        if len(result) == 0:
            Logger.instance().warning("[Vm] PCI VGA NOT FOUND")
            return Pci.PciList()

        if len(result.get_vga_list()) > 1:
            Logger.instance().warning("[Vm] Multiple VGA FOUND")  # fixme utopia Дать выбрать какой VGA пробрасывать
            return Pci.PciList()

        iommu_group = result[0].iommu_group
        if iommu_group is None:
            Logger.instance().warning("[Vm] VGA does not include to iommu group")
            return Pci.PciList()

        return result

    def __get_usb_host_list_for_passthrough(self, pci_list):
        if not self.__initiate_usb_host_passthrough:
            return Pci.PciList()

        result = pci_list.get_usb_host_list()
        if len(result) == 0:
            Logger.instance().warning("[Vm] PCI USB Host NOT FOUND")
            return Pci.PciList()

        iommu_group = result[0].iommu_group
        if iommu_group is None:
            Logger.instance().warning("[Vm] PCI USB host does not include to iommu group")
            return Pci.PciList()

        return result

    def __get_isa_bridge_list_for_passthrough(self, pci_list):
        if not self.__initiate_isa_bridge_passthrough:
            return Pci.PciList()

        result = pci_list.get_isa_bridge_list()
        if len(result) == 0:
            Logger.instance().warning("[Vm] PCI ISA bridge NOT FOUND")
            return Pci.PciList()

        iommu_group = result[0].iommu_group
        if iommu_group is None:
            Logger.instance().warning("[Vm] PCI ISA bridge does not include to iommu group")
            return Pci.PciList()

        return result

    def __run(self):
        network_bridge = NetworkBridge(self.__project_config.get_server_name(),
                                       self.__project_config.get_vm_bridge_ip_address_and_mask(),
                                       self.__project_config.get_dns_config_dir_path(),
                                       self.__project_config.get_internet_network_interface(),
                                       block_internet_access=self.__block_internet_access,
                                       dns_suffix=self.__project_config.get_dns_suffix(),
                                       my_host=self.__project_config.get_my_host())

        vm_registry = VmRegistry(self.__project_config.get_vm_registry_dir_path())
        vm_meta_data = vm_registry.get_with_verifying(self.__vm_name)

        local_network_interface = OpenVpnConfig.get_or_default_local_network_interface(
            self.__project_config.get_local_network_interface())

        vm_ssh_forwarding = VmSshForwarding(vm_meta_data, local_network_interface,
                                            vm_meta_data.get_ssh_forward_port())
        vm_rdp_forwarding = VmRdpForwarding(vm_meta_data, local_network_interface,
                                            vm_meta_data.get_rdp_forward_port())
        tcp_forwarding_thread = threading.Thread(target=lambda: (vm_ssh_forwarding.add_with_retry(),
                                                                 vm_rdp_forwarding.add_with_retry()))
        tcp_forwarding_thread.start()

        if self.__initiate_isa_bridge_passthrough and self.__initiate_builtin_kbd_and_mouse_passthrough:
            self.__initiate_builtin_kbd_and_mouse_passthrough = False
            Logger.instance().warning(
                "[Vm] ignore --builtin_kbd_and_mouse_passthrough parameter because of --initiate_isa_bridge_passthrough parameter enabled")

        qemu_builtin_kbd_and_mouse_passthrough = None
        if self.__initiate_builtin_kbd_and_mouse_passthrough:
            qemu_builtin_kbd_and_mouse_passthrough = QemuBuiltinKeyboardAndMousePassthrough()

        vm = VirtualMachine(network_bridge, vm_meta_data,
                            qemu_pci_passthrough=self.__qemu_pci_passthrough,
                            qemu_platform=QemuPlatform(vm_meta_data, self.__vm_platform),
                            qemu_cdrom=QemuCdRom(self.__os_distr_path, Virtio(self.__project_config).get_win_drivers()),
                            qemu_builtin_kbd_and_mouse_passthrough=qemu_builtin_kbd_and_mouse_passthrough)
        vm.run()
        tcp_forwarding_thread.join()


class OsNameAndVersion:
    def __init__(self, name_and_version):
        self.__name_and_version = name_and_version

    def is_windows(self):
        return self.__name_and_version.lower().startswith('win')

    def is_linux(self):
        return self.__name_and_version.lower().startswith('linux')

    def compare(self):
        return False

    # Изменить версию win для wine https://forum.winehq.org/viewtopic.php?t=14589


class WindowsCommandLineWrapper:
    def get_command_line(self, cmd):
        return cmd


class LinuxCommandLineWrapper:
    def get_command_line(self, cmd):
        return cmd

    # https://stackoverflow.com/questions/26809898/invoke-msys2-shell-from-command-prompt-or-powershell
    # https://stackoverflow.com/questions/1681208/python-platform-independent-way-to-modify-path-environment-variable


class Msys2CommandLineWrapper:
    MSYS2_DIR_DEFAULT = fr"C:\msys64"

    def __init__(self, msys2_dir=MSYS2_DIR_DEFAULT):
        self.__msys2_dir = msys2_dir

    def get_command_line(self, cmd):
        # fixme utopia Экранирование для cmd (shlex?)
        # https://docs.python.org/3/library/shlex.html#shlex.quote
        # https://stackoverflow.com/questions/33560364/python-windows-parsing-command-lines-with-shlex
        self.__setup_path()
        return fr'"{self.__get_msys2_bash_path()}" -c "{cmd}"'

    def __setup_path(self):
        print("fixme")

    def __get_msys2_bash_path(self):
        return fr"{self.__get_msys2_bin_dir()}\bash.exe"

    def __get_msys2_bin_dir(self):
        return fr"{self.__msys2_dir}\usr\bin"


# wine cmd /C ""notepad" "привет мир \'.txt""
# Файлы в win не могут содержать двоичные кавычки в названии
# fixme utopia Проверить экранирование одинарной кавычки на винде
# fixme utopia Использовать WindowsCommandLineWrapper?
class WineCommandLineWrapper:
    WINE = "wine"

    def get_command_line(self, cmd):
        # fixme utopia Экранирование для cmd (shlex?)
        return fr'"{self.WINE}" cmd /C "{cmd}"'


class CommandLineExecutor:
    def __init__(self, command_line):
        self.__command_line = command_line

    def run(self, cmd):
        subprocess.check_call(self.__command_line.get_command_line(cmd), shell=True)

    # https://www.blog.pythonlibrary.org/2010/03/03/finding-installed-software-using-python/


class WindowsInstallerInnoSetup:
    def __init__(self):
        print("")


class WindowsInstallerMsi:
    def __init__(self):
        print("")

    # inherit from interface PaketManagerInstaller
    # Ubuntu / LinuxMint / Debian / termux
    # https://stackoverflow.com/questions/57610644/linux-package-management-with-python
    # https://habr.com/ru/articles/683716/
    # https://askubuntu.com/a/548087


class AptPackageManagerInstaller:
    def __init__(self, package_name, command_line_executor=CommandLineExecutor(LinuxCommandLineWrapper())):
        self.__package_name = package_name
        self.__command_line_executor = command_line_executor

    def is_installed(self):
        return False

    def install_from_file(self, path_to_installer_file):
        print("")

    def install(self):
        print("")

    def uninstall(self):
        print("")

    def add_ppa(self):
        print("")

    # https://phoenixnap.com/kb/install-rpm-packages-on-ubuntu


class RmpForUbuntuPackageManagerInstaller:
    def __init__(self):
        print("")

    # inherit from interface PaketManagerInstallers
    # CentOs


class YumPackageManagerInstaller:
    def __init__(self):
        print("")

    # inherit from interface PaketManagerInstallers
    # ArchLinux / MSYS2-Windows (передать соответствующий CommandLineForInstaller)


class PackmanPackageManagerInstaller:
    def __init__(self):
        print("")

    def is_installed(self):
        return False

    def install_from_file(self, path_to_installer_file):
        print("")

    def install(self):
        print("")

    def uninstall(self):
        print("")

    # https://wiki.archlinux.org/title/wine
    def enable_multilib(self):
        print("")

    # fedora / centos / rhel


class DnfPackageManagerInstaller:
    def __init__(self):
        print("")

    def add_repo(self):
        print("")

    # Если скачивает torrent, то закачивает торрент при помощи transmission
    # (использовать https://pypi.org/project/python-magic/ для определения типа скачанного файла)


class Downloader:
    def __init__(self):
        print("")

    # https://habr.com/ru/articles/658463/


class TransmissionDaemon:
    def __init__(self):
        print("")


class PackageName:
    def __init__(self):
        print("")

    def get_name(self):
        return ""

    def get_os(self):
        return ""


class PackageAction:
    def __init__(self):
        print("")

    # winetrics + wine 32|64
    def install(self):
        # dependency installer

        if self.__is_packet_manager():
            if os == "Windows" and current_os == "Windows":
                PackmanPaketManagerInstaller(Msys2CommandLineForInstaller()).install(packet)
            if os == "Windows" and current_os == "Linux":
                PackmanPaketManagerInstaller(WineCommandLineForInstaller(Msys2CommandLineForInstaller())).install(
                    packet)
            if os == "Ubuntu" and current_os == "Ubuntu":
                AptPaketManagerInstaller(LinuxCommandLineForInstaller()).install(packet)
        elif self.__is_download_and_install():
            download()  # if download_file is torrent --> dowload_torrent
            # if download archive (zip / tar / rar) --> unpack_archive to tmp folder
            if downloaded_file == "exe":  # inno setup installer
                if os == "Windows" and current_os == "Windows":
                    WindowsInstallerInnoSetup(WindowsCommandLineForInstaller()).install(custom_command_line)
                if os == "Windows" and current_os == "Linux":
                    WindowsInstallerInnoSetup(WineCommandLineForInstaller()).install(custom_command_line)
            if downloaded_file == "msi":  # inno setup installer
                if os == "Windows" and current_os == "Windows":
                    WindowsInstallerMsi(WindowsCommandLineForInstaller()).install(custom_command_line)
                if os == "Windows" and current_os == "Linux":
                    WindowsInstallerMsi(WineCommandLineForInstaller()).install(custom_command_line)
            if downloaded_file == "deb":
                if os == "Ubuntu" and current_os == "Ubuntu":
                    AptPaketManagerInstaller(LinuxCommandLineForInstaller()).install_from_file()
            if downloaded_file == "rpm":
                if os == "CentOs" and current_os == "CentOs":
                    YumPaketManagerInstaller(LinuxCommandLineForInstaller()).install_from_file()

    def __packet_manager(self):
        return False

    def __is_download_and_install(self):
        return False


class InstallCommandLine:
    def __init__(self):
        print("")


def main():
    project_config = OpenVpnConfig()
    parser = argparse.ArgumentParser(prog=project_config.get_server_name(), description="HomeVpn project executable")

    subparsers = parser.add_subparsers(help="Subcommands help", dest='command')

    parser_config = subparsers.add_parser("config", help="Get project main config parameter value by name")
    parser_config.add_argument("config_parameter_name", type=str, help="Config parameter name")

    parser_run = subparsers.add_parser("run", help="Run VPN server")

    parser_check = subparsers.add_parser("check", help="Check UDP hole punching")

    parser_user_ovpn = subparsers.add_parser("user_ovpn", help="Generate ovpn file for user")
    parser_user_ovpn.add_argument("user_name", type=str, help="User name")

    parser_vm_create = subparsers.add_parser("vm_create", help="Create virtual machine image")
    parser_vm_create.add_argument("vm_name", type=str, help="Virtual machine name")
    parser_vm_create.add_argument("--image_size", type=int, help="Virtual machine image size in gibibytes", default=50)

    parser_vm_run = subparsers.add_parser("vm_run", help="Run virtual machine")
    parser_vm_run.add_argument("vm_name", type=str, help="Virtual machine name")
    parser_vm_run.add_argument("--bi", help="Block internet access, but not the local network",
                               action='store_true')
    parser_vm_run.add_argument("--vga_passthrough", help="Initiate VGA PCI passthrough to virtual machine",
                               action='store_true')
    parser_vm_run.add_argument("--vga_audio_passthrough",
                               help="Initiate VGA PCI audio (HDMI audio, DisplayPort audio) passthrough to virtual machine",
                               action='store_true')
    parser_vm_run.add_argument("--vm_platform", type=str,
                               help=f"QEMU platform: {', '.join(QemuPlatform.QEMU_PLATFORM_LIST)}",
                               default=QemuPlatform.QEMU_PLATFORM_I440FX_BIOS)
    parser_vm_run.add_argument("--usb_host_passthrough",
                               help="Initiate all USB host PCI passthrough to virtual machine",
                               action='store_true')
    parser_vm_run.add_argument("--isa_bridge_passthrough",
                               help="Initiate ISA bridge (laptop keyboard, touchpad and others) PCI passthrough to virtual machine",
                               action='store_true')
    parser_vm_run.add_argument("--builtin_kbd_and_mouse_passthrough",
                               help="Builtin keyboard and mouse passthrough. Relevant for laptops. If use --isa_bridge_passthrough parameter --builtin_kbd_and_mouse_passthrough parameter disabled because PCI ISA bridge usually contains connection to builtin keyboard and mouse. Recommended use this parameter with --vga_passthrough",
                               action='store_true')
    parser_vm_run.add_argument("--asc_override_patched_kernel",
                               help="Download, install and configure ASC override patched Linux kernel. See https://wiki.archlinux.org/title/PCI_passthrough_via_OVMF#Bypassing_the_IOMMU_groups_(ACS_override_patch)",
                               action='store_true')
    parser_vm_run.add_argument("--os_distr_path", type=Path, help="OS distributive iso image path")
    parser_vm_run.add_argument("--qemu_pci_passthrough", type=QemuPciPassthrough,
                               help="PCI VGA list for passthrough to virtual machine. Not for human use")
    parser_vm_run.add_argument("--grub_config_backup_path", type=Path,
                               help="Grub config backup file path. Not for human use")

    parser_vm_ssh_fwd = subparsers.add_parser("vm_ssh_fwd", help="Port forwarding for SSH for virtual machine")
    parser_vm_ssh_fwd.add_argument("vm_name", type=str, help="Virtual machine name")
    parser_vm_ssh_fwd.add_argument("host_tcp_port", type=int,
                                   help="Host PC input TCP port for forwarding SSH connection to target virtual machine",
                                   choices=range(TcpPort.TCP_PORT_MIN, TcpPort.TCP_PORT_MAX),
                                   metavar=f"{TcpPort.TCP_PORT_MIN}..{TcpPort.TCP_PORT_MAX}")

    parser_vm_rdp_fwd = subparsers.add_parser("vm_rdp_fwd", help="Port forwarding for RDP for virtual machine")
    parser_vm_rdp_fwd.add_argument("vm_name", type=str, help="Virtual machine name")
    parser_vm_rdp_fwd.add_argument("host_tcp_port", type=int,
                                   help="Host PC input TCP port for forwarding SSH connection to target virtual machine",
                                   choices=range(TcpPort.TCP_PORT_MIN, TcpPort.TCP_PORT_MAX),
                                   metavar=f"{TcpPort.TCP_PORT_MIN}..{TcpPort.TCP_PORT_MAX}")

    parser_startup = subparsers.add_parser(StartupCrontab.COMMAND, help="Startup action script")

    parser_test = subparsers.add_parser("test", help="TEST")

    args = parser.parse_args()
    if args.command == "config":
        print(project_config.get_config_parameter_strong(args.config_parameter_name))

    elif args.command == "run":
        asyncio.run(Daemon().run())

    elif args.command == "check":
        MyExternalIpAddressAndPort(project_config.get_server_port()).get()

    elif args.command == "user_ovpn":
        my_ip_address_and_port = IpAddressAndPort(
            TextConfigReader(project_config.get_my_current_ip_address_and_port()).get())
        print(OpenVpnClientConfigGenerator(my_ip_address_and_port, args.user_name).generate())

    elif args.command == "vm_create":
        print(VmRegistry(project_config.get_vm_registry_dir_path()).create(args.vm_name,
                                                                           args.image_size).get_image_path())

    elif args.command == "vm_run":
        VmRunner(args.vm_name, project_config=project_config,
                 block_internet_access=args.bi,
                 initiate_vga_passthrough=args.vga_passthrough,
                 initiate_vga_audio_passthrough=args.vga_audio_passthrough,
                 initiate_usb_host_passthrough=args.usb_host_passthrough,
                 initiate_isa_bridge_passthrough=args.isa_bridge_passthrough,
                 initiate_builtin_kbd_and_mouse_passthrough=args.builtin_kbd_and_mouse_passthrough,
                 asc_override_patched_kernel=args.asc_override_patched_kernel,
                 qemu_pci_passthrough=args.qemu_pci_passthrough,
                 grub_config_backup_path=args.grub_config_backup_path,
                 vm_platform=args.vm_platform,
                 os_distr_path=args.os_distr_path).run()

    elif args.command == "vm_ssh_fwd":
        vm_registry = VmRegistry(project_config.get_vm_registry_dir_path())
        vm_registry.set_ssh_forward_port(args.vm_name, args.host_tcp_port)

    elif args.command == "vm_rdp_fwd":
        vm_registry = VmRegistry(project_config.get_vm_registry_dir_path())
        vm_registry.set_rdp_forward_port(args.vm_name, args.host_tcp_port)

    elif args.command == "test":
        print(VmRegistry("./vm").list())
        return

        label_file_path = Path("./test_label.txt")
        script = f'"{sys.executable}" -c "import datetime; import pathlib; pathlib.Path(\\"{label_file_path}\\").write_text(str(datetime.datetime.now()))"'
        Startup().register_script(script, is_execute_once=True)
        Power().reboot()
        return

        # pci_list = Pci.get_list()
        # print(pci_list.get_vga_list()[0].get_rom("/home/utopia"))
        # print(pci_list.get_pci_list_by_capabilities(is_pci_express=True, is_sriov=False))
        # print(Cpu.get_cpu0().is_intel_above_sandybridge())
        # print(Cpu.get_cpu0().is_intel_above_broadwell())
        # return
        #
        # LinuxKernel().download_and_install_liquorix_kernel()
        # # subprocess.check_call("/home/utopia/test.sh", shell=True)
        # print(f"FFF {CurrentOs.is_ubuntu_or_like()}")
        # print(Grub().get_last_liquorix_kernel_path())
        # print(Grub().get_last_normal_kernel_path())
        # return
        # sv = semantic_version.Version("6.14.0-91-fuck")
        # print(sv.major)
        # print(sv.minor)
        # print(sv.patch)
        # print(sv.prerelease)
        # print(sv.build)
        # sv2 = semantic_version.Version("6.14.0-1-generic")
        # print(sv > sv2)
        # return
        # # https://insights-core.readthedocs.io/en/latest/shared_parsers_catalog/grub_conf.html
        # # https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/7/html/system_administrators_guide/ch-working_with_the_grub_2_boot_loader#sec-Editing_a_Menu_Entry
        # grub_cfg = TextConfigReader("/boot/grub/grub.cfg").get()
        #
        # _regex = regex.compile("[\n\r\t ]*(submenu|menuentry) [^{}]*{((?>(?R)|[^{}]*)+?)}")
        # tmp = _regex.findall(grub_cfg)
        #
        # for bb in tmp:
        #     print(bb)
        #     print("\n")
        #
        # return
        # print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
        # pci_list = Pci.get_list()  # .get_vga_list(with_consumer=True)
        # print(pci_list.is_iommu_enabled())
        # return
        #
        # usb_host_controller_list = pci_list.get_usb_host_list()
        # print(usb_host_controller_list)
        # if not pci_list.is_each_device_in_its_own_iommu_group(pci_list):
        #     print("GGGGGG")
        # else:
        #     print("FFFFFFF")
        #
        # print([{"vfio_pci.ids": [pci.get_id() for pci in pci_list]}])

        ggg = ConfigParser().find_all(TextConfigReader("/etc/default/grub").get(), as_ast=True)
        print(ggg)
        print(LinuxKernelParamsParser().find_all(ggg["GRUB_CMDLINE_LINUX"], as_ast=True))


    elif args.command == StartupCrontab.COMMAND:
        Startup().run_all_scripts()


if __name__ == '__main__':
    main()
