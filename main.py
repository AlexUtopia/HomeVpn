import argparse
import asyncio
import copy
import multiprocessing
import shutil
import atexit
import os.path
import re
import subprocess
import json
import ipaddress
import tempfile
import time
import sys
import urllib.request
import urllib.parse
import uuid

import filelock
import unittest
import pathlib

import requests

# fixme utopia Исправление для iptc который неадекватно работает на Ubuntu 22.04


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


from lib.python.logger import *
from lib.python.network import *
from lib.python.project import *
from lib.python.startup import *
from lib.python.system import *
from lib.python.types import *
from lib.python.utils import *
from lib.python.utils.binary import *
from lib.python.utils.regex import *
from lib.python.system import *
from lib.python.qemu import QemuRam


# fixme utopia Проверить на многопроцессорных системах (у меня есть)
class Cpu(BaseParser):
    # https://gcc.gnu.org/git/?p=gcc.git;a=blob;f=gcc/common/config/i386/cpuinfo.h;h=a6ede14a3ccb9f5e5eaa8866e2f29c35d3234285;hb=HEAD
    # https://codeberg.org/smxi/inxi/src/branch/master/inxi#L12095
    # https://github.com/torvalds/linux/blob/master/arch/x86/events/intel/core.c#L6527
    # https://en.wikichip.org/wiki/intel/microarchitectures
    # https://en.wikipedia.org/wiki/CPUID
    # https://www.etallen.com/cpuid.html

    class Win11SupportedCpu:
        __ENCODING = "utf-8"
        __DATA_DIR_PATH = pathlib.Path(str(Path("data"))) / "win11_supported_cpu"

        class CpuDescriptor:
            def __init__(self, cpu_descriptor_as_string):
                vendor_brand_model = cpu_descriptor_as_string.lower().split("\t")
                self.__vendor = vendor_brand_model[0]
                self.__brand = vendor_brand_model[1]
                self.__model = vendor_brand_model[2]

            def __eq__(self, other):
                if other is self:
                    return True
                elif isinstance(other, str):
                    cpu_name = other.lower()
                    return self.__compare(cpu_name, self.get_cpu_name_variants())
                elif isinstance(other, Cpu.Win11SupportedCpu.CpuDescriptor):
                    return (self.get_vendor() == other.get_vendor()) and (self.get_brand() == other.get_brand()) and (
                            self.get_model() == other.get_model())
                else:
                    return False

            def get_cpu_name_variants(self):
                delimiter = " "
                result = set()
                for vendor in self.get_vendor_variants():
                    for brand in self.get_brand_variants():
                        for model in self.get_model_variants():
                            if not model:
                                continue
                            cpu_name = []
                            if vendor:
                                cpu_name.append(vendor)
                            if brand:
                                cpu_name.append(brand)
                            cpu_name.append(model)
                            if cpu_name:
                                result.add(delimiter.join(cpu_name))
                                if vendor and brand and vendor == brand:
                                    result.add(f"{vendor}{delimiter}{model}")
                return result

            def get_vendor(self):
                return self.__vendor

            def get_vendor_variants(self):
                vendor = self.get_vendor()
                return {vendor, self.__replace_trade_mark(vendor), self.__remove_trade_mark(vendor)}

            def get_brand(self):
                return self.__brand

            def get_brand_variants(self):
                brand = self.get_brand()
                return {brand, self.__replace_trade_mark(brand), self.__remove_trade_mark(brand),
                        self.__remove_processor(brand)}

            def get_model(self):
                return self.__model

            def get_model_variants(self):
                model = self.get_model()
                return {model, self.__remove_processor(model), self.__replace_processor(model, " "),
                        self.__replace_processor(model, "-")}

            def __remove_trade_mark(self, value):
                result = value
                result = result.replace("®", "")
                result = result.replace("(r)", "")
                result = result.replace("™", "")
                result = result.replace("(tm)", "")
                return result

            def __replace_trade_mark(self, value):
                result = value
                result = result.replace("®", "(r)")
                result = result.replace("™", "(tm)")
                return result

            def __remove_processor(self, value):
                result = value
                result = result.replace("processor ", "")
                result = result.replace(" processor", "")
                result = result.replace("processor", "")
                return result

            def __replace_processor(self, value, new=" "):
                result = value
                result = result.replace(" processor ", new)
                return result

            def __compare(self, test_string, value_variants):
                for value_variant in value_variants:
                    if value_variant in test_string:
                        return True
                return False

        def __init__(self):
            pass

        def is_support(self, cpu_name):
            for cpu_list_by_vendor_file_path in self.__DATA_DIR_PATH.iterdir():
                if cpu_list_by_vendor_file_path.is_file() or cpu_list_by_vendor_file_path.resolve().is_file():
                    with open(cpu_list_by_vendor_file_path, mode="rt",
                              encoding=self.__ENCODING) as cpu_list_by_vendor_file:
                        for index, line in enumerate(cpu_list_by_vendor_file, 1):
                            cpu_descriptor = Cpu.Win11SupportedCpu.CpuDescriptor(line.rstrip('\n'))
                            if cpu_descriptor == cpu_name:
                                return True
            return False

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

    @staticmethod
    def is_win11_support():
        return Cpu.Win11SupportedCpu().is_support(cpuinfo.get_cpu_info()["brand_raw"])

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
        result = r"\(uarch synth\) ="
        result += fr" {tmp.get_regex_for(Cpu.__CPU_VENDOR)}"
        result += fr"(?: {tmp.get_regex_for(Cpu.__CPU_UARCH)})?"
        result += fr"(?> \{{{tmp.get_regex_for(Cpu.__CPU_UARCH_FAMILY)}\}})?"
        result += fr"(?>, {tmp.get_regex_for(Cpu.__CPU_TECHNICAL_PROCESS)})?"
        result += "$"
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
    ENCODING = "utf-8"

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

    def test_cpu_name_variants(self):
        for path in (pathlib.Path(str(Path("data"))) / "test" / "UnitTest_Cpu" / "test_cpu_name_variants").iterdir():
            input_data = (path / "input.txt").read_text(encoding=self.ENCODING)
            expected_result = set(json.loads(
                (path / "expected_result.json").read_text(encoding=self.ENCODING)))

            result = Cpu.Win11SupportedCpu().CpuDescriptor(input_data).get_cpu_name_variants()
            self.assertEqual(result, expected_result)

    def test_win11_supported_cpu(self):
        test_data = [
            ("11th Gen Intel(R) Core(TM) i5-1145G7 @ 2.60GHz", True),
            ("11th Gen Intel(R) Core(TM) i5-1135G7 @ 2.40GHz", True),
            ("Intel Core i5-1135G7", True),
            ("Intel(R) Core(TM) i7-2640M CPU @ 2.80GHz", False),
            ("", False),
            ("qwertyuiop[]", False),
            ("Intel Core ", False),
            ("AMD", False)
        ]

        for cpu_name, expected_result in test_data:
            result = Cpu.Win11SupportedCpu().is_support(cpu_name)
            self.assertEqual(result, expected_result, msg=cpu_name)


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

    def add_nameserver(self, nameserver_ip_address):
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


# https://wiki.archlinux.org/title/Systemd-resolved
# https://manpages.debian.org/testing/resolvconf/resolvconf.8.en.html
class ResolvConf2:
    ENCODING = "utf-8"
    EXTENSION = "conf"
    RESOLV_CONF_PATH = pathlib.Path("/etc/resolv.conf")

    # https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html#Process%20Exit%20Codes
    __SYSTEMD_EXIT_CODE_EXIT_FAILURE = 1

    def __init__(self, project_name, config_dir_path=pathlib.Path("/etc/systemd/resolved.conf.d")):
        self.__project_name = project_name
        self.__config_dir_path = pathlib.Path(str(config_dir_path))
        atexit.register(self.__clear_at_exit)

    def add_nameserver(self, nameserver_ip_address):
        nameserver_ip_address = self.__to_ip_address(nameserver_ip_address)
        self.__config_dir_path.mkdir(parents=True, exist_ok=True)
        nameserver_file_path = self.__get_nameserver_file_path(nameserver_ip_address)
        nameserver_file_path.write_text(self.__make_content(nameserver_ip_address), encoding=self.ENCODING)
        self.__restart_systemd_resolved()
        return nameserver_file_path

    def remove_nameserver(self, nameserver_ip_address):
        nameserver_ip_address = self.__to_ip_address(nameserver_ip_address)
        nameserver_file_path = self.__get_nameserver_file_path(nameserver_ip_address)
        if nameserver_file_path.exists():
            nameserver_file_path.unlink()
            self.__restart_systemd_resolved()
        return nameserver_file_path

    def __clear_at_exit(self):
        for nameserver_file_path in self.__config_dir_path.glob(f"{self.__project_name}_*.{self.EXTENSION}"):
            nameserver_file_path.unlink()

    def __to_ip_address(self, nameserver_ip_address):
        return ipaddress.ip_address(str(nameserver_ip_address))

    def __restart_systemd_resolved(self):
        sleep_time_before_next_attempt_list = [2, 8, 12, 16]
        number_of_attempts = len(sleep_time_before_next_attempt_list) + 1
        for attempt in range(number_of_attempts):
            try:
                subprocess.check_call("systemctl restart systemd-resolved.service", shell=True)
                return
            except subprocess.CalledProcessError as ex:
                if (ex.returncode == self.__SYSTEMD_EXIT_CODE_EXIT_FAILURE) and (attempt < number_of_attempts - 1):
                    sleep_time_before_next_attempt = sleep_time_before_next_attempt_list[attempt]
                    Logger.instance().warning(
                        f"[ResolvConf] Restart systemd-resolved FAIL: {ex} (attempt = {attempt + 1}/{number_of_attempts}, sleep = {sleep_time_before_next_attempt} seconds)")
                    time.sleep(sleep_time_before_next_attempt)
                else:
                    Logger.instance().error(
                        f"[ResolvConf] Restart systemd-resolved FAIL: {ex}")
                    raise ex

    def __make_content(self, nameserver_ip_address):
        return f"[Resolve]\nDNS={nameserver_ip_address} {NetworkInterface.GOOGLE_PUBLIC_DNS_IPV4_1}\nDomains={DnsDhcpProvider.DNS_SUFFIX_DEFAULT}"

    def __get_nameserver_file_path(self, nameserver_ip_address):
        return self.__config_dir_path / self.__get_nameserver_file_name(nameserver_ip_address)

    def __get_nameserver_file_name(self, nameserver_ip_address):
        return f"{self.__project_name}_{nameserver_ip_address}.{self.EXTENSION}"


class UnitTest_ResolvConf2(unittest.TestCase):
    PROJECT_NAME = "name"

    def test_nameserver_ip_address_invalid(self):
        nameserver_ip_address = "hello world!!!"
        with tempfile.TemporaryDirectory() as temp_dir_path:
            temp_dir_path = pathlib.Path(temp_dir_path)

            resolv_conf = ResolvConf2(self.PROJECT_NAME, config_dir_path=temp_dir_path)
            with self.assertRaises(ValueError):
                resolv_conf.add_nameserver(nameserver_ip_address)

    def test_config_dir_is_file(self):
        nameserver_ip_address = "127.0.0.13"
        with tempfile.NamedTemporaryFile() as temp_file:
            resolv_conf = ResolvConf2(self.PROJECT_NAME, config_dir_path=temp_file.name)
            with self.assertRaises(FileExistsError):
                resolv_conf.add_nameserver(nameserver_ip_address)

    def test_config_file_is_dir(self):
        nameserver_ip_address = "127.0.0.13"
        with tempfile.TemporaryDirectory() as temp_dir_path:
            temp_dir_path = pathlib.Path(temp_dir_path)

            resolv_conf = ResolvConf2(self.PROJECT_NAME, config_dir_path=temp_dir_path)
            resolv_conf._ResolvConf2__get_nameserver_file_path(nameserver_ip_address).mkdir()
            with self.assertRaises(IsADirectoryError):
                resolv_conf.add_nameserver(nameserver_ip_address)

    def test_void_remove_nameserver(self):
        nameserver_ip_address = "127.0.0.13"
        with tempfile.TemporaryDirectory() as temp_dir_path:
            temp_dir_path = pathlib.Path(temp_dir_path)

            resolv_conf = ResolvConf2(self.PROJECT_NAME, config_dir_path=temp_dir_path)
            self.assertFalse(resolv_conf._ResolvConf2__get_nameserver_file_path(nameserver_ip_address).exists())
            self.assertFalse(resolv_conf.remove_nameserver(nameserver_ip_address).exists())

    def test_clear_at_exit(self):
        nameserver_ip_address1 = "127.0.0.13"
        nameserver_ip_address2 = "127.0.0.14"
        with tempfile.TemporaryDirectory() as temp_dir_path:
            temp_dir_path = pathlib.Path(temp_dir_path)

            resolv_conf = ResolvConf2(self.PROJECT_NAME, config_dir_path=temp_dir_path)

            nameserver_ip_address1_file_path = resolv_conf.add_nameserver(nameserver_ip_address1)
            self.assertTrue(nameserver_ip_address1_file_path.exists() and nameserver_ip_address1_file_path.is_file())
            self.__check_nameserver_file_content(nameserver_ip_address1, resolv_conf)

            resolv_conf.add_nameserver(nameserver_ip_address2)
            self.__check_nameserver_file_content(nameserver_ip_address2, resolv_conf)
            nameserver_ip_address2_file_path = resolv_conf.add_nameserver(nameserver_ip_address2)
            self.__check_nameserver_file_content(nameserver_ip_address2, resolv_conf)
            self.assertTrue(nameserver_ip_address2_file_path.exists() and nameserver_ip_address2_file_path.is_file())

            temp_file_path = temp_dir_path / "temp.file"
            temp_file_path.touch()

            resolv_conf._ResolvConf2__clear_at_exit()

            for path in temp_dir_path.iterdir():
                self.assertEqual(path, temp_file_path)

    def test(self):
        nameserver_ip_address1 = "127.128.129.130"
        nameserver_ip_address2 = "127.128.129.131"
        resolv_conf = ResolvConf2(self.PROJECT_NAME)
        resolv_conf.add_nameserver(nameserver_ip_address1)
        resolv_conf.add_nameserver(nameserver_ip_address2)

        self.__check_nameserver_list([nameserver_ip_address1, nameserver_ip_address2])

        self.assertFalse(resolv_conf.remove_nameserver(nameserver_ip_address2).exists())
        self.__check_nameserver_list([nameserver_ip_address1])

        self.assertFalse(resolv_conf.remove_nameserver(nameserver_ip_address1).exists())
        self.__check_nameserver_list([])

    def __check_nameserver_list(self, nameserver_ip_address_list):
        cmd_result = subprocess.run("resolvectl dns", shell=True, capture_output=True, text=True)
        self.assertFalse(bool(cmd_result.returncode), msg=str(cmd_result))

        for nameserver_ip_address in nameserver_ip_address_list:
            regex = re.compile(fr'^Global:.*{re.escape(nameserver_ip_address)}.*$', flags=re.MULTILINE)
            find_result = regex.findall(cmd_result.stdout)
            self.assertEqual(len(find_result), 1)

    def __check_nameserver_file_content(self, nameserver_ip_address, resolv_conf):
        self.assertEqual(resolv_conf._ResolvConf2__get_nameserver_file_path(nameserver_ip_address).read_text(
            encoding=ResolvConf2.ENCODING),
            resolv_conf._ResolvConf2__make_content(nameserver_ip_address))



# https://serverfault.com/questions/723292/dnsmasq-doesnt-automatically-reload-when-entry-is-added-to-etc-hosts
# https://thekelleys.org.uk/dnsmasq/docs/dnsmasq-man.html --dhcp-hostsdir
# https://psutil.readthedocs.io/en/latest/#psutil.net_if_addrs psutil.AF_LINK (17) - получить MAC адрес сетевого интерфейса
# Сгенерировать MAC адрес
# Внимательно посмотреть на опцию --dhcp-host - она позволяет биндить mac address на hostname
# Генерируем рандомный mac адрес https://stackoverflow.com/questions/8484877/mac-address-generator-in-python
class DnsDhcpProvider(DaemonManagerBase):
    EXTENSION = "host"
    DNS_SUFFIX_DEFAULT = "homevpn.org"

    @staticmethod
    def get_hostname(name, dns_suffix=DNS_SUFFIX_DEFAULT):
        return f"{name}.{dns_suffix}"

    MY_HOST_DEFAULT = get_hostname("myhost")

    def __init__(self, interface, dhcp_host_dir="./dhcp-hostsdir", resolv_conf=ResolvConf2("HomeVpn"),
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
        return f"{name}.{self.EXTENSION}"

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
        subprocess.check_call(f"resolvectl dns {self.__interface} {self.__interface.get_ipv4_interface_if().ip}",
                              shell=True)
        # self.__resolv_conf.add_nameserver(self.__get_target_interface_ip_address())

    def __remove_dnsmasq_from_system_dsn_servers_list(self):
        subprocess.check_call(f"resolvectl dns {self.__interface}", shell=True)
        # self.__resolv_conf.remove_nameserver(self.__get_target_interface_ip_address())

    def __get_target_interface_ip_address(self):
        return self.__interface_ip_interface.ip


# https://builtin.com/software-engineering-perspectives/python-class-decorator
class IpcLockDecorator:
    PROCESSES_DIR_NAME = "processes"

    def __init__(self, mutex_dir_path=Path(".tmp")):
        self.__interprocess_lock = filelock.FileLock(pathlib.Path(str(mutex_dir_path)) / "lock.lock")
        self.__processes_locks_dir_path = pathlib.Path(str(mutex_dir_path)) / self.PROCESSES_DIR_NAME
        self.__my_process_lock = filelock.FileLock(
            self.__processes_locks_dir_path / self.__get_my_process_lock_file_name())

    def lock(self, func):
        with self.__interprocess_lock:
            self.__my_process_acquire()
            return func()

    def close(self, func):
        with self.__interprocess_lock:
            if self.__check_close():
                result = func()
                self.__my_process_release()
                self.__clear_processes_locks_dir()
                return result
            else:
                self.__my_process_release()
        return None

    def __check_close(self):
        my_process_lock_file_path = pathlib.Path(self.__my_process_lock.lock_file)
        if self.__processes_locks_dir_path.exists() and self.__processes_locks_dir_path.is_dir():
            for path in self.__processes_locks_dir_path.iterdir():
                if path == my_process_lock_file_path:
                    continue
                lock = filelock.FileLock(path, timeout=0)
                try:
                    lock.acquire()
                    if not lock.is_locked:
                        return False
                except:
                    return False
                finally:
                    lock.release()
        return True

    def __my_process_acquire(self):
        if not self.__my_process_lock.is_locked:
            self.__my_process_lock.acquire()

    def __my_process_release(self):
        self.__my_process_lock.release()

    def __clear_processes_locks_dir(self):
        shutil.rmtree(self.__processes_locks_dir_path, ignore_errors=True)

    def __get_my_process_lock_file_name(self):
        return f"{os.getpid()}.lock"


class UnitTest_IpcLockDecorator(unittest.TestCase):
    TEST_DIR_PATH = pathlib.Path(str(Path("data"))) / "test" / "UnitTest_IpcLockDecorator"

    def test_abandoned_behavior(self):
        p1, p1_queue = self.__make_and_start_process("p1")
        self.assertEqual(p1_queue.get(), "p1 locked")

        p2, p2_queue = self.__make_and_start_process("p2")

        p1.kill()
        p1.join()

        self.assertTrue((self.TEST_DIR_PATH / IpcLockDecorator.PROCESSES_DIR_NAME).exists())
        self.assertEqual(p2_queue.get(), "p2 locked")
        self.assertEqual(p2_queue.get(), "p2 unlocked")
        self.assertEqual(p2_queue.get(), "p2 exit")
        p2.join()

        p1_queue.close()
        p2_queue.close()

        self.assertFalse((self.TEST_DIR_PATH / IpcLockDecorator.PROCESSES_DIR_NAME).exists())

    def test_normal_close(self):
        p1, p1_queue = self.__make_and_start_process("p1", sleep_in_lock_sec=0.1, sleep_sec=10)
        self.assertEqual(p1_queue.get(), "p1 locked")

        self.assertTrue((self.TEST_DIR_PATH / IpcLockDecorator.PROCESSES_DIR_NAME).exists())

        p2, p2_queue = self.__make_and_start_process("p2", sleep_in_lock_sec=0.1, sleep_sec=10)
        self.assertEqual(p2_queue.get(), "p2 locked")

        p3, p3_queue = self.__make_and_start_process("p3", sleep_in_lock_sec=0.1, sleep_sec=10)
        self.assertEqual(p3_queue.get(), "p3 locked")

        self.assertEqual(p1_queue.get(), "p1 exit")
        p1.join()

        self.assertEqual(p2_queue.get(), "p2 exit")
        p2.join()

        # Управляемый раздельно ресурс закрывает второй процесс
        self.assertEqual(p3_queue.get(), "p3 unlocked")
        self.assertEqual(p3_queue.get(), "p3 exit")
        p3.join()

        p1_queue.close()
        p2_queue.close()
        p3_queue.close()

        self.assertFalse((self.TEST_DIR_PATH / IpcLockDecorator.PROCESSES_DIR_NAME).exists())

    def test_emergency_close(self):
        p1, p1_queue = self.__make_and_start_process("p1", sleep_in_lock_sec=0.1, sleep_sec=10)
        self.assertEqual(p1_queue.get(), "p1 locked")

        self.assertTrue((self.TEST_DIR_PATH / IpcLockDecorator.PROCESSES_DIR_NAME).exists())

        p2, p2_queue = self.__make_and_start_process("p2", sleep_in_lock_sec=0.1, sleep_sec=10)
        self.assertEqual(p2_queue.get(), "p2 locked")

        p1.kill()
        p2.kill()
        p1.join()
        p2.join()

        # Директория с файлами-локами процессов осталась, т.к. последний процесс был убит и не смог произвести очистку
        self.assertTrue((self.TEST_DIR_PATH / IpcLockDecorator.PROCESSES_DIR_NAME).exists())

        # Запускаем новый процесс который зачистит директорию с файлами-локами по завершении
        p3, p3_queue = self.__make_and_start_process("p3", sleep_in_lock_sec=0, sleep_sec=0)
        self.assertEqual(p3_queue.get(), "p3 locked")
        self.assertEqual(p3_queue.get(), "p3 unlocked")
        self.assertEqual(p3_queue.get(), "p3 exit")
        p3.join()

        self.assertFalse((self.TEST_DIR_PATH / IpcLockDecorator.PROCESSES_DIR_NAME).exists())

        p1_queue.close()
        p2_queue.close()
        p3_queue.close()

    def test_only_close(self):
        self.assertFalse((self.TEST_DIR_PATH / IpcLockDecorator.PROCESSES_DIR_NAME).exists())

        p1, p1_queue = self.__make_and_start_process("p1", sleep_in_lock_sec=0, sleep_sec=0, is_only_close=True)
        self.assertEqual(p1_queue.get(), "p1 unlocked")
        self.assertEqual(p1_queue.get(), "p1 exit")
        p1.join()

        self.assertFalse((self.TEST_DIR_PATH / IpcLockDecorator.PROCESSES_DIR_NAME).exists())

        p1_queue.close()

    def __make_and_start_process(self, name, sleep_in_lock_sec=10, sleep_sec=0, is_only_close=False):
        queue = multiprocessing.Queue()
        process = multiprocessing.Process(target=UnitTest_IpcLockDecorator.__worker,
                                          args=(name, queue, sleep_in_lock_sec, sleep_sec, is_only_close))
        process.start()
        self.assertEqual(queue.get(), f"{name} started")
        return process, queue

    @staticmethod
    def __worker(name, queue, sleep_in_lock_sec=10, sleep_sec=0, is_only_close=False):
        locker = IpcLockDecorator(UnitTest_IpcLockDecorator.TEST_DIR_PATH)

        queue.put(f"{name} started")

        if not is_only_close:
            locker.lock(lambda: (
                queue.put(f"{name} locked"),
                time.sleep(sleep_in_lock_sec)
            ))

        time.sleep(sleep_sec)

        locker.close(lambda: (
            queue.put(f"{name} unlocked"),
        ))

        queue.put(f"{name} exit")


class NetworkBridge:
    def __init__(self, name, bridge_ip_address_and_mask,
                 dhcp_host_dir="./dhcp-hostsdir", internet_network_interface=None, block_internet_access=False,
                 dns_suffix=DnsDhcpProvider.DNS_SUFFIX_DEFAULT, my_host=DnsDhcpProvider.MY_HOST_DEFAULT):
        self.__lock_decorator = IpcLockDecorator(pathlib.Path(str(Path("data"))) / "network_bridge")
        self.__interface = NetworkInterface("{}-bridge".format(name))
        self.__bridge_ip_address_and_mask = ipaddress.ip_interface(bridge_ip_address_and_mask)

        if internet_network_interface is not None:
            self.__internet_network_interface = NetworkInterface(internet_network_interface)
            Logger.instance().debug(
                f"[NetworkBridge] Internet network interface SET MANUALLY: {self.__internet_network_interface}")
        else:
            self.__internet_network_interface = None

        self.__dns_dhcp_provider = DnsDhcpProvider(self.__interface, dhcp_host_dir, dns_suffix=dns_suffix,
                                                   my_host=my_host, resolv_conf=ResolvConf2(name))
        self.__block_internet_access = block_internet_access
        atexit.register(self.close)

    @staticmethod
    def __lock(func):
        def __decorate_func(self, *args, **kwargs):
            self.__lock_decorator.lock(lambda: func(self, *args, **kwargs))

        return __decorate_func

    @staticmethod
    def __close_lock(func):
        def __decorate_func(self, *args, **kwargs):
            self.__lock_decorator.close(lambda: func(self, *args, **kwargs))

        return __decorate_func

    @__lock
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
            Logger.instance().error(f"[NetworkBridge] Create FAIL: {ex}")
            self.close()

    @__close_lock
    def close(self):
        if not self.__interface.exists():
            return

        self.__clear_firewall()
        self.__clear_bridge_dns_dhcp()

        subprocess.check_call("ip link set {} down".format(self.__interface), shell=True)
        subprocess.check_call("ip link delete {} type bridge".format(self.__interface), shell=True)

    @__lock
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


class UnitTest_FileLock(unittest.TestCase):
    def test_abandoned_behavior(self):
        p1, p1_queue = self.__make_and_start_process("p1")
        self.assertEqual(p1_queue.get(), "p1 locked")

        p2, p2_queue = self.__make_and_start_process("p2")

        p1.kill()
        p1.join()

        self.assertEqual(p2_queue.get(), "p2 locked")
        self.assertEqual(p2_queue.get(), "p2 exit")
        p2.join()

        p1_queue.close()
        p2_queue.close()

    def __make_and_start_process(self, name):
        queue = multiprocessing.Queue()
        process = multiprocessing.Process(target=UnitTest_FileLock.__worker, args=(name, queue))
        process.start()
        self.assertEqual(queue.get(), f"{name} started")
        return process, queue

    @staticmethod
    def __worker(name, queue):
        queue.put(f"{name} started")
        lock = filelock.FileLock(str(Path("data/test/UnitTest_FileLocker/test_abandoned_behavior/test_lock.lock")))
        with lock:
            queue.put(f"{name} locked")
            time.sleep(10)
        queue.put(f"{name} exit")


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


class VmTcpForwarding:
    RETRY_COUNT = 30

    def __init__(self, vm_meta_data, local_network_if, input_port, output_port):
        self.__vm_meta_data = vm_meta_data
        self.__local_network_if = NetworkInterface(local_network_if)
        self.__input_port = input_port
        self.__output_port = TcpPort(output_port)
        self.__vm_ip_address = None
        atexit.register(self.__clear_at_exit)

    def add(self):
        if not self.__is_valid_input_port():
            Logger.instance().debug(f"[VmTcpForwarding:{self.__input_port}] PORT INVALID")
            return
        if self.__vm_ip_address:
            Logger.instance().debug(f"[VmTcpForwarding:{self.__input_port}] ALREADY")
            return
        Logger.instance().debug(
            f'[VmTcpForwarding:{self.__input_port}] "{self.__vm_meta_data.get_name()}": {self.__local_network_if}:{self.__input_port} --> {self.__get_vm_destination_ip_address_and_port()}')
        self.__iptables_rule()

    def add_with_retry(self, stop_event=None):
        sleep_sec = 5
        for i in range(VmTcpForwarding.RETRY_COUNT):
            try:
                Logger.instance().debug(f"[VmTcpForwarding:{self.__input_port}] Try {i + 1}")
                self.add()
                Logger.instance().debug(f"[VmTcpForwarding:{self.__input_port}] OK")
                return
            except Exception as ex:
                Logger.instance().warning(f"[VmTcpForwarding:{self.__input_port}] FAIL: {ex}")
                if i == VmTcpForwarding.RETRY_COUNT - 1:
                    Logger.instance().error(f"[VmTcpForwarding:{self.__input_port}] ATTEMPTS OVER")
                    return
                if stop_event:
                    if stop_event.wait(sleep_sec):
                        Logger.instance().warning(f"[VmTcpForwarding:{self.__input_port}] INTERRUPT")
                        return
                else:
                    time.sleep(sleep_sec)

    def clear(self):
        if not self.__is_valid_input_port():
            return
        if not self.__vm_ip_address:
            return
        self.__iptables_rule(clear=True)
        self.__vm_ip_address = None

    def __clear_at_exit(self):
        try:
            self.clear()
        except Exception as ex:
            Logger.instance().error(f"[VmTcpForwarding:{self.__input_port}] Clear FAIL: {ex}")

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
        if self.__vm_ip_address:
            return IpAddressAndPort(self.__vm_ip_address, self.__output_port)

        self.__vm_ip_address = self.__vm_meta_data.get_ip_address_strong()
        return IpAddressAndPort(self.__vm_ip_address, self.__output_port)


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
        else:  # Ключи без значений
            _key_list = key_list
            if not _key_list:
                _key_list = [str(config)]
            result_ref[str(config)] = Normalizer.EmptyValue()

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



class UnitTest_AsyncRunner(unittest.TestCase):
    __EXIT_CODE = 55
    __SHELL_EXIT_CODE_COMMAND_NOT_FOUND_IN_THE_SYSTEMS_PATH = 127

    def test(self):
        asyncio.run(self.__run_success())
        asyncio.run(self.__run_non_existing_script())

    async def __run_success(self):
        async_script_runner = AsyncRunner()
        script1 = TextConfigWriter("data/test/script1.sh")

        test_script = f"""echo "message 0"
sleep 1

echo "message 1"
sleep 1

echo "message 2"

exit {self.__EXIT_CODE}   
"""
        script1.set(test_script, set_executable=True)
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

    parser_vm_run = subparsers.add_parser("vm_run", help="Run virtual machine",
                                          formatter_class=argparse.RawTextHelpFormatter)
    parser_vm_run.add_argument("vm_name", type=str, help="Virtual machine name")
    parser_vm_run.add_argument("--bi", help="Block internet access, but not the local network",
                               action='store_true')
    parser_vm_run.add_argument("--vm_platform", type=str,
                               help=f"QEMU platform (default %(default)s)",
                               choices=list(QemuPlatform.QEMU_PLATFORM_LIST),
                               default=QemuPlatform.QEMU_PLATFORM_I440FX_BIOS)
    parser_vm_run.add_argument("-m", type=QemuRam,
                               help=f"Virtual machine RAM size in MibiBytes (default %(default)s MiB)",
                               default=QemuRam())
    parser_vm_run.add_argument("--vm_host_mode", help="Virtual machine using as main OS for current PC",
                               action='store_true')
    parser_vm_run.add_argument("--vga_passthrough", type=PciPassthroughMode.argparse, choices=list(PciPassthroughMode),
                               help=f"Initiate VGA PCI passthrough to virtual machine (default %(default)s)\n{PciPassthroughMode.get_help()}",
                               default=PciPassthroughMode.NONE)
    parser_vm_run.add_argument("--vga_audio_passthrough", type=PciPassthroughMode.argparse,
                               choices=list(PciPassthroughMode),
                               help=f"Initiate VGA PCI audio (HDMI audio, DisplayPort audio) passthrough to virtual machine (default %(default)s)\n{PciPassthroughMode.get_help()}",
                               default=PciPassthroughMode.NONE)
    parser_vm_run.add_argument("--usb_host_passthrough", type=PciPassthroughMode.argparse,
                               choices=list(PciPassthroughMode),
                               help=f"Initiate all USB host (UHCI/OHCI/EHCI/XHCI) PCI passthrough to virtual machine (default %(default)s)\n{PciPassthroughMode.get_help()}",
                               default=PciPassthroughMode.NONE)
    parser_vm_run.add_argument("--isa_bridge_passthrough", type=PciPassthroughMode.argparse,
                               choices=list(PciPassthroughMode),
                               help=f"Initiate ISA bridge (laptop keyboard, touchpad and others) PCI passthrough to virtual machine (default %(default)s)\n{PciPassthroughMode.get_help()}",
                               default=PciPassthroughMode.NONE)
    parser_vm_run.add_argument("--builtin_kbd_and_mouse_passthrough",
                               help="Builtin keyboard and mouse passthrough. Relevant for laptops.\nIf use --isa_bridge_passthrough parameter --builtin_kbd_and_mouse_passthrough parameter will be disabled\nbecause PCI ISA bridge usually contains connection to builtin keyboard and mouse.\nRecommended use this parameter with --vga_passthrough",
                               action='store_true')
    parser_vm_run.add_argument("--asc_override_patched_kernel",
                               help="Download, install and configure ASC override patched Linux kernel.\nSee https://wiki.archlinux.org/title/PCI_passthrough_via_OVMF#Bypassing_the_IOMMU_groups_(ACS_override_patch)",
                               action='store_true')
    parser_vm_run.add_argument("--os_distr_path", type=Path, help="OS distributive iso image path")
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

    parser_test = subparsers.add_parser("test", help="TEST")

    try:
        args = parser.parse_args()
        args_dict = vars(args)
        # Print the result
        print(args_dict)
    except Exception as ex:
        Logger.instance().error(ex)
        return
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
                 ram=args.m,
                 os_distr_path=args.os_distr_path,
                 vm_host_mode=args.vm_host_mode).run()

    elif args.command == "vm_ssh_fwd":
        vm_registry = VmRegistry(project_config.get_vm_registry_dir_path())
        vm_registry.set_ssh_forward_port(args.vm_name, args.host_tcp_port)

    elif args.command == "vm_rdp_fwd":
        vm_registry = VmRegistry(project_config.get_vm_registry_dir_path())
        vm_registry.set_rdp_forward_port(args.vm_name, args.host_tcp_port)

    elif args.command == "test":
        pci_list = Pci.get_list()
        #print(pci_list.get_vga_list())
        #print(list(pci_list.get_vga_list())[0].get_rom(pathlib.Path("/home/galina")))

        #print(Pci.get_list().get_pci_id_list())
        return

        print(Pci.get_list().is_vfio_pci_applied())
        return

        print(VmRegistry("./vm").list())
        return

        label_file_path = Path("./test_label.txt")
        script = f'"{sys.executable}" -c "import datetime; import pathlib; pathlib.Path(\\"{label_file_path}\\").write_text(str(datetime.datetime.now()))"'
        Startup().register_script(script, is_execute_once=True)
        Power().reboot()
        return

        #
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



if __name__ == '__main__':
    main()
