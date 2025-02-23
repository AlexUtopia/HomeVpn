import argparse
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
import threading
import time
import sys
import urllib.request
import urllib.parse
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
                    fmt='{asctime} {levelname: <8} [{process}][{thread}] <{funcName}:{lineno}>\t\t{message}',
                    style='{'))
            self.__logger.addHandler(file_handler)

        def get_logger(self):
            return self.__logger

        def __get_log_file_path(self):
            return os.path.join(self.__get_logging_dir_path(),
                                f"{datetime.datetime.now():%Y-%m-%d}_{self.__LOG_NAME}.log")

        def __get_logging_dir_path(self):
            result = os.path.join(self.__get_current_dir_path(), "logs")
            os.makedirs(result)
            return result

        def __get_current_dir_path(self):
            return os.path.dirname(os.path.realpath(__file__))

    __instance = LoggerImpl()

    @staticmethod
    def instance():
        return Logger.__instance.get_logger()


# https://tproger.ru/translations/demystifying-decorators-in-python/

# https://devblogs.microsoft.com/oldnewthing/20050201-00/?p=36553
# https://stackoverflow.com/a/43512141
# https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-osversioninfoexa#remarks
class CurrentOs:
    @staticmethod
    def is_windows():
        # https://docs.python.org/3/library/sys.html#sys.platform
        return sys.platform.lower().startswith('win')

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
        # https://docs.python.org/3/library/os.html#os.uname
        return semantic_version.Version(platform.release())

    @staticmethod
    def get_windows_version():
        os_version_info_ex = sys.getwindowsversion()
        # fixme utopia Добавить информацию про wProductType
        return semantic_version.Version(major=os_version_info_ex.major, minor=os_version_info_ex.minor,
                                        build=os_version_info_ex.build)

    @staticmethod
    def get_linux_distro_name():
        # https://pypi.org/project/os-release/
        # https://www.freedesktop.org/software/systemd/man/os-release.html
        return os_release.id()

    @staticmethod
    def get_linux_distro_version():
        # https://pypi.org/project/os-release/
        # https://www.freedesktop.org/software/systemd/man/os-release.html
        return semantic_version.Version(version_string=os_release.version_id())

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
    def create_backup(self, backup_prefix=f"unused_since_{datetime.datetime.now():%Y-%m-%dT%H_%M_%S_%f%z}_"):
        if not self.exists():
            return None

        backup_file_path = self.get_dir_path().join(f"{backup_prefix}{self.get_filename()}")
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

    def set_with_backup(self, data, set_executable=False):
        if self.__config_file_path.exists():
            self.__last_backup_file_path = self.__config_file_path.create_backup()
        self.set(data, set_executable)
        return self.get_last_backup_file_path()

    def get_last_backup_file_path(self):
        return self.__last_backup_file_path

    def restore_from_backup(self, is_remove_backup=False):
        if self.__last_backup_file_path is None or not self.__last_backup_file_path.exist():
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
            f"NAT type: {nat_type}\nUDP hole punching: {self.__nat_adapted_for_udp_hole_punching(nat_type)}")
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
        Logger.instance().debug(f"STUN server: {hostname}:{port}")
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
                print("My external IP address and port: {}".format(result))
                return result
            except Exception as ex:
                print("[WARNING] Get my IP address and port FAIL (but we continue): {}".format(ex))
        raise Exception("My external IP address and port NOT FOUND")


class OpenVpnServer:
    OPEN_VPN = "openvpn"

    def __init__(self, config_file_path):
        self.__config_file_path = str(config_file_path)

    def run(self):
        result = subprocess.run(
            [self.OPEN_VPN, "--config", self.__config_file_path, "--daemon"],
            text=True
        )
        Logger.instance().debug(f"[OpenVpnServer] Return: {result}")

        if result.returncode:
            raise Exception(f"[OpenVpnServer] Start FAIL: {result.stderr}")

        Logger.instance().debug("[OpenVpnServer] Start OK")


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
            print("Telegram send message: {}".format(f.read().decode(self.ENCODING)))

    # https://core.telegram.org/bots/api#senddocument
    def send_file(self, file_path):
        _file_path = Path(file_path)
        files = {'document': (_file_path.get_filename(), open(_file_path.get(), 'rb'), "multipart/form-data")}
        response = requests.post(self.__get_send_document_url(), data={"chat_id": self.__config["chat_id"]},
                                 files=files)
        print("Telegram send document: {}".format(response.content))

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

    def get_vm_registry_path(self):
        return self.get_config_parameter_strong("vm_registry_path")

    def get_vm_dir(self):
        return os.path.dirname(self.get_vm_registry_path())

    def get_internet_network_interface(self):
        result = self.get_config_parameter("internet_network_interface")
        if result is None:
            return result
        return NetworkInterface(result)

    @staticmethod
    def get_or_default_internet_network_interface(internet_network_interface_from_config):
        if internet_network_interface_from_config is None:
            result = NetworkInterface.get_internet_if()
            print("Internet network interface: {}".format(result))
            return result
        print("Internet network interface SET MANUALLY: {}".format(internet_network_interface_from_config))
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
            print("Local network interface: {}".format(result))
            return result
        print("Local network interface SET MANUALLY: {}".format(local_network_interface))
        return NetworkInterface(local_network_interface)

    def get_dns_config_dir(self):
        return self.get_config_parameter_strong("dns_config_dir")

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


# Make network bridge
# 1)
# ip link add name br0 type bridge
# ip addr add 172.20.0.1/16 dev br0
# ip link set br0 up
# [X] dnsmasq --interface=br0 --bind-interfaces --dhcp-range=172.20.0.2,172.20.255.254

# 2)
# sysctl net.ipv4.ip_forward=1

# 3)
# iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE
# iptables -A FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT

# Make tap device

# 1)
# https://docs.python.org/3/library/getpass.html#getpass.getuser
# https://gist.github.com/arvati/546617042fcf2669f330b739075c1c5d
# https://community.openvpn.net/openvpn/wiki/ManagingWindowsTAPDrivers
# ip tuntap add dev tap0 mode tap user "YOUR_USER_NAME_HERE"
# ip link set tap0 up promisc on
# ip link set tap0 master br0 [нужно? - понять]

# 2)
# set ip address manually

# 3) https://stackoverflow.com/questions/3837069/how-to-get-network-interface-card-names-in-python
# iptables -A FORWARD -i tap0 -o wlan0 -j ACCEPT

# https://scapy.readthedocs.io/en/latest/api/scapy.sendrecv.html?highlight=bridge_and_sniff#scapy.sendrecv.bridge_and_sniff
# https://stackoverflow.com/questions/9337545/writing-an-ethernet-bridge-in-python-with-scapy
# https://gist.github.com/mgalgs/1856631

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
            print("FFF: {}".format(ex))

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
        print(iptc.easy.dump_table(iptc.Table.FILTER, ipv6=False))

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
        print(iptc.easy.dump_table(iptc.Table.NAT, ipv6=False))

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
        print(iptc.easy.dump_table(iptc.Table.FILTER, ipv6=False))


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
    def __init__(self, name, image_path, mac_address, ssh_forward_port=None, rdp_forward_port=None):
        self.__name = VmName(name)
        self.__image_path = Path(image_path)
        self.__mac_address = netaddr.EUI(str(mac_address))
        self.__ssh_forward_port = None
        self.set_ssh_forward_port(ssh_forward_port)
        self.__rdp_forward_port = None
        self.set_rdp_forward_port(rdp_forward_port)

    def __str__(self):
        return str(self.to_dict())

    def __repr__(self):
        return self.__str__()

    @staticmethod
    def from_dict(name, vm_registry_as_dict):
        name_filtered_as_string = str(VmName(name))
        meta_data_as_dict = vm_registry_as_dict.get(name_filtered_as_string)
        if meta_data_as_dict is None:
            return None
        return VmMetaData(name_filtered_as_string, meta_data_as_dict.get("image_path"),
                          meta_data_as_dict.get("mac_address"), meta_data_as_dict.get("ssh_forward_port"),
                          meta_data_as_dict.get("rdp_forward_port"))

    @staticmethod
    def from_dict_strong(name, vm_registry_as_dict):
        result = VmMetaData.from_dict(name, vm_registry_as_dict)
        if result is None:
            raise Exception("VM \"{}\" not found in registry".format(name))
        return result

    def append_to_dict_force(self, vm_registry_as_dict):
        vm_registry_as_dict.update(self.to_dict())

    def to_dict(self):
        name_as_string = str(self.get_name())
        image_path_as_string = str(self.get_image_path())
        mac_address_as_string = str(self.get_mac_address())
        result = {name_as_string: {"image_path": image_path_as_string,
                                   "mac_address": mac_address_as_string}}

        if self.__ssh_forward_port is not None:
            result[name_as_string].update({"ssh_forward_port": int(self.__ssh_forward_port)})

        if self.__rdp_forward_port is not None:
            result[name_as_string].update({"rdp_forward_port": int(self.__rdp_forward_port)})

        return result

    def get_name(self):
        return str(self.__name)

    def get_image_path(self):
        return str(self.__image_path)

    def image_exists(self):
        return self.__image_path.exists() and os.path.isfile(self.get_image_path())

    def get_mac_address(self):
        return self.__mac_address

    def get_mac_address_as_string(self):
        result = self.__mac_address
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
        return self.__ssh_forward_port

    def set_ssh_forward_port(self, ssh_forward_port):
        if ssh_forward_port is None:
            self.__ssh_forward_port = None
        else:
            self.__ssh_forward_port = TcpPort(ssh_forward_port)

    def get_rdp_forward_port(self):
        return self.__rdp_forward_port

    def set_rdp_forward_port(self, rdp_forward_port):
        if rdp_forward_port is None:
            self.__rdp_forward_port = None
        else:
            self.__rdp_forward_port = TcpPort(rdp_forward_port)

    def get_working_dir_path(self):
        return self.__image_path.get_dir_path().join(f"{self.get_name()}-data")


class VmRegistry:
    # {
    #   "vm1_name":
    #   {
    #     "image_path":  (String)
    #     "mac_address": (String)
    #   },
    #   "vm2_name": { ... }
    # }
    #

    __IMAGE_FORMAT = "qcow2"
    __IMAGE_EXTENSION = ".img"

    def __init__(self, vm_registry_config_path):
        self.__registry_reader = JsonConfigReader(vm_registry_config_path)
        self.__registry_writer = JsonConfigWriter(vm_registry_config_path)
        self.__registry_as_dict = dict()
        self.__vm_dir_default = Path(os.path.dirname(vm_registry_config_path))

    # Инсталлируем ОС через VirtualMachine( VmRegistry().create( vm_name, size_in_gib ), path_to_iso_installer = "/path/to/os_installer.iso" )
    # Добавляем виртуалку в реестр при помощи

    def create(self, name, image_size_in_gib=20):
        self.__load_registry()
        self.__check_non_exists(name)
        result = self.__build_meta_data(name)
        if result.image_exists():
            # fixme utopia Если образ есть а метаданных нет, то нужно метаданные сохранить в реестр
            #              тем самым можно восстановить реестр по имеющимся образам
            raise Exception("VM image \"{}\" EXISTS. Please change VM name or rename/move/delete current image".format(
                result.get_image_path()))

        command_line = self.__create_image_command_line(result, image_size_in_gib)
        print(command_line)
        subprocess.check_call(command_line, shell=True)
        self.__add_to_registry(result)
        self.__save_registry()
        return result

    def list(self):
        self.__load_registry()
        result = []
        for name in self.__registry_as_dict:
            meta_data = self.__get_meta_data(name)
            if meta_data is not None:
                result.append(meta_data)
        return result

    def get_with_verifying(self, name):
        self.__load_registry()
        meta_data = self.__get_meta_data(name)
        if not VmRegistry.__image_exists(meta_data):
            raise Exception("VM image \"{}\" NOT FOUND".format(name))
        return meta_data

    def get_path_to_image_with_verifying(self, name):
        return self.get_with_verifying(name).get_image_path()

    def set_ssh_forward_port(self, name, ssh_forward_port):
        meta_data = self.get_with_verifying(name)
        meta_data.set_ssh_forward_port(ssh_forward_port)
        self.__add_to_registry(meta_data)
        self.__save_registry()

    def set_rdp_forward_port(self, name, rdp_forward_port):
        meta_data = self.get_with_verifying(name)
        meta_data.set_rdp_forward_port(rdp_forward_port)
        self.__add_to_registry(meta_data)
        self.__save_registry()

    def __create_image_command_line(self, meta_data, image_size_in_gib):
        return "qemu-img create -f {} \"{}\" {}G".format(self.__IMAGE_FORMAT, meta_data.get_image_path(),
                                                         image_size_in_gib)

    def __build_meta_data(self, name):
        return VmMetaData(name, self.__get_image_path(name), VmRegistry.__generate_random_mac_address())

    def __get_image_path(self, name):
        return os.path.join(str(self.__vm_dir_default), self.__get_image_filename(name))

    def __get_image_filename(self, name):
        return "{}{}".format(VmName(name), self.__IMAGE_EXTENSION)

    @staticmethod
    def __generate_random_mac_address():
        return randmac.RandMac()

    def __check_non_exists(self, name):
        meta_data = self.__get_meta_data(name)
        if VmRegistry.__image_exists(meta_data):
            raise Exception("VM with name \"{}\" already exist ({})".format(name, meta_data))

    @staticmethod
    def __image_exists(meta_data):
        return meta_data is not None and meta_data.image_exists()

    def __add_to_registry(self, meta_data):
        meta_data.append_to_dict_force(self.__registry_as_dict)

    def __get_meta_data(self, name):
        return VmMetaData.from_dict(name, self.__registry_as_dict)

    def __save_registry(self):
        self.__registry_writer.set(self.__registry_as_dict)

    def __load_registry(self):
        self.__registry_as_dict = self.__registry_reader.get_or_create_if_non_exists()


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
    def __init__(self):
        self.__command_line = None
        atexit.register(self.clear_at_exit)

    def start(self):
        if self.__command_line:
            return

        self._start_impl()
        self.__command_line = str(self._build_command_line())

        print(self.__command_line)
        subprocess.check_call(self.__command_line, shell=True)

    def close(self):
        if not self.__command_line:
            return

        self.__find_and_kill_target_processes()
        self._close_impl()

    def clear_at_exit(self):
        try:
            self.close()
        except Exception:
            return

    def __find_and_kill_target_processes(self):
        for process in psutil.process_iter():
            if self.__compare_cmd_line(process.cmdline()):
                print("KILL {}".format(process))
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
class DnsDhcpProvider:
    __HOST_EXTENSION = ".host"

    def __init__(self, interface, dhcp_host_dir="./dhcp-hostsdir", resolv_conf=ResolvConf()):
        self.__interface = interface
        self.__dhcp_host_dir = Path(dhcp_host_dir)
        self.__resolv_conf = resolv_conf
        self.__dnsmasq_command_line = str()
        self.__interface_ip_interface = ipaddress.IPv4Interface("192.168.0.1/24")
        atexit.register(self.stop)

    def start(self):
        if self.__dnsmasq_command_line:
            return

        self.__make_dhcp_host_dir()
        self.__interface_ip_interface = self.__interface.get_ipv4_interface_if()
        if self.__interface_ip_interface is None:
            raise Exception("Target interface \"{}\" ipv4 address NOT ASSIGN".format(self.__interface))
        self.__dnsmasq_command_line = self.__build_dnsmasq_command_line()

        self.__add_dnsmasq_to_system_dsn_servers_list()
        print(self.__dnsmasq_command_line)
        subprocess.check_call(self.__dnsmasq_command_line, shell=True)

    def stop(self):
        if not self.__dnsmasq_command_line:
            return

        self.__find_and_kill_target_dnsmasq_processes()
        self.__remove_dnsmasq_from_system_dsn_servers_list()

    def add_host(self, vm_meta_data):
        TextConfigWriter(self.__get_dhcp_host_file_path(vm_meta_data)).set(
            self.__build_dhcp_host_file_content(vm_meta_data))

    def __build_dnsmasq_command_line(self):
        return "dnsmasq --interface={} --bind-interfaces --dhcp-hostsdir=\"{}\" {}".format(
            self.__interface, self.__dhcp_host_dir, self.__get_dhcp_range_parameter())

    def __make_dhcp_host_dir(self):
        self.__dhcp_host_dir.makedirs()

    def __get_dhcp_host_file_path(self, vm_meta_data):
        return os.path.join(str(self.__dhcp_host_dir), self.__get_dhcp_host_file_name(vm_meta_data.get_name()))

    def __get_dhcp_host_file_name(self, name):
        return "{}{}".format(name, self.__HOST_EXTENSION)

    @staticmethod
    def __build_dhcp_host_file_content(vm_meta_data):
        return "{},{}".format(vm_meta_data.get_mac_address_as_string(), vm_meta_data.get_name())

    def __find_and_kill_target_dnsmasq_processes(self):
        for process in psutil.process_iter():
            if self.__compare_cmd_line(process.cmdline()):
                print("KILL {}".format(process))
                process.kill()

    def __compare_cmd_line(self, psutil_process_cmdline):
        normalize_command_line = " ".join(shlex.split(self.__dnsmasq_command_line))
        psutil_command_line = " ".join(psutil_process_cmdline)
        return psutil_command_line.endswith(normalize_command_line)

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
                 dhcp_host_dir="./dhcp-hostsdir", internet_network_interface=None, block_internet_access=False):
        self.__interface = NetworkInterface("{}-bridge".format(name))
        self.__bridge_ip_address_and_mask = ipaddress.ip_interface(bridge_ip_address_and_mask)

        if internet_network_interface is not None:
            self.__internet_network_interface = NetworkInterface(internet_network_interface)
            print("Internet network interface SET MANUALLY: {}".format(self.__internet_network_interface))
        else:
            self.__internet_network_interface = None

        self.__dns_dhcp_provider = DnsDhcpProvider(self.__interface, dhcp_host_dir)
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
            print("Setup VM bridge FAIL: {}".format(ex))
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
        print("Internet network interface: {}".format(self.__internet_network_interface))
        BridgeFirewall(self.__interface, self.__internet_network_interface, self.__block_internet_access).setup()

    def __clear_firewall(self):
        try:
            BridgeFirewall(self.__interface, self.__internet_network_interface,
                           self.__block_internet_access).clear_at_exit()
        except Exception as ex:
            print("[WARNING] Clear firewall FAIL: {}".format(ex))

    def __setup_bridge_dns_dhcp(self):
        self.__dns_dhcp_provider.start()

    def __clear_bridge_dns_dhcp(self):
        self.__dns_dhcp_provider.stop()

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
            print("Virtio win drivers was downloaded: \"{}\"".format(win_drivers_iso_path))
            return win_drivers_iso_path

        self.__download_win_drivers(win_drivers_iso_path)
        return win_drivers_iso_path

    def __get_win_drivers_iso_path(self):
        return Path(os.path.join(self.__get_and_make_vm_dir(), Virtio.__WIN_DRIVERS_FILENAME))

    def __get_and_make_vm_dir(self):
        result = self.__project_config.get_vm_dir()
        Path(result).makedirs()
        return result

    def __download_win_drivers(self, win_drivers_iso_path):
        virtio_win_drivers_url = self.__project_config.get_virtio_win_drivers_url()

        print("Virtio win drivers DOWNLOAD: {} --> \"{}\"".format(virtio_win_drivers_url, win_drivers_iso_path))
        urllib.request.urlretrieve(virtio_win_drivers_url, str(win_drivers_iso_path))
        print("Virtio win drivers DOWNLOAD: OK")


class UdpWatchdog:
    __IPTABLES_RULE_MATCH = "string"
    __CONTER_MISMATCH = 3

    def __init__(self, open_vpn_config, my_external_ip_address_and_port):
        self.__is_init = False
        self.__secret_message = "testtest"  # fixme utopia Сгенерировать uuid?
        self.__counter = int(0)
        self.__open_vpn_config = open_vpn_config
        self.__my_external_ip_address_and_port = my_external_ip_address_and_port
        atexit.register(self.clear_at_exit)

    # fixme utopia Если три раза подряд метод __check_drop_packets_counter() возвращал False, то вернуть False
    def watch(self):
        if not self.__is_init:
            self.__setup_firewall()
            self.__is_init = True

        try:
            self.__send_upd_packet_to_my_external_ip_address_and_port()
        except Exception as ex:
            print("[Watchdog] Send UDP packet FAIL: {}".format(ex))
            return False

        time.sleep(1)
        return self.__check_drop_packets_counter()

    def clear_at_exit(self):
        try:
            if self.__is_init:
                self.__setup_firewall(clear=True)
        except Exception:
            return

    def __send_upd_packet_to_my_external_ip_address_and_port(self):
        ip_address = self.__my_external_ip_address_and_port.get_ip_address()
        udp_port = self.__my_external_ip_address_and_port.get_port()

        sock_tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_tx.sendto(self.__get_secret_message_for_send(), (str(ip_address), udp_port))
        self.__counter = self.__counter + 1

    def __get_secret_message_for_send(self):
        return bytes("{}/{}".format(self.__secret_message, self.__counter), "utf-8")

    def __setup_firewall(self, clear=False):
        # iptables -I INPUT -p udp -m string --string "testtest" --algo bm -j DROP
        table = iptc.Table(iptc.Table.FILTER)
        chain = iptc.Chain(table, "INPUT")

        rule = iptc.Rule()
        rule.protocol = "udp"

        # fixme utopia Задать параметр to
        # https://ipset.netfilter.org/iptables-extensions.man.html#lbCE
        match = iptc.Match(rule, self.__IPTABLES_RULE_MATCH)
        match.string = str(self.__secret_message)
        match.algo = "bm"
        rule.add_match(match)

        target = iptc.Target(rule, "DROP")
        rule.target = target

        if clear:
            chain.delete_rule(rule)
        else:
            chain.insert_rule(rule)
        table.commit()
        print(iptc.easy.dump_table(iptc.Table.FILTER, ipv6=False))

    def __check_drop_packets_counter(self):
        drop_packets_counter = self.__get_drop_packets_counter()
        if drop_packets_counter is None:
            # fixme utopia По идее здесь надо заново настраивать файервол
            print("[Watchdog] drop_packets_counter is null: {}".format(
                iptc.easy.dump_table(iptc.Table.FILTER, ipv6=False)))
            self.__setup_firewall()
            return False

        conters_match = self.__counter == drop_packets_counter
        # fixme utopia Облогировать
        result = conters_match if conters_match else self.__counter <= drop_packets_counter + self.__CONTER_MISMATCH

        # fixme utopia Нужно выравнивать счётчики (т.е. self.__counter = drop_packets_counter) если разница между ними константна некоторое время

        print("[Watchdog] send_packets={} | drop_packets={} | {}".format(self.__counter, drop_packets_counter,
                                                                         "GOOD" if result else "BAD"))
        return result

    def __get_drop_packets_counter(self):
        table = iptc.Table(iptc.Table.FILTER)
        table.refresh()
        chain = iptc.Chain(table, 'INPUT')
        for rule in chain.rules:
            for match in rule.matches:
                if match.name == self.__IPTABLES_RULE_MATCH:
                    return rule.get_counters()[0]
        return None


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
        if type(val) is str:
            result = int(val, base)
        elif type(val) is int:
            result = val
        else:
            raise Exception("Value unknown type: {}".format(str(val)))
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
    def get_digit_count_max(base):
        BitUtils.__check_base(base)
        int_max = BitUtils.get_int_max_value(BitUtils.BIT_COUNT_MAX, signed=False)
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


# https://pcisig.com/sites/default/files/files/PCI_Code-ID_r_1_11__v24_Jan_2019.pdf
class PciClassCode(int):
    BASE_CLASS_BACKWARD_COMPATIBILITY = 0x00
    BASE_CLASS_BACKWARD_COMPATIBILITY_ALL_EXCEPT_VGA = 0x00
    BASE_CLASS_BACKWARD_COMPATIBILITY_VGA = 0x01
    BASE_CLASS_VGA = 0x03

    REGEX = "[0-9a-fA-F]{4}"  # fixme utopia Использовать BitUtils.get_regex

    def __new__(cls, class_code):
        return super(PciClassCode, cls).__new__(cls, BitUtils.get_int_with_check(class_code, bit_count=16, signed=False,
                                                                                 base=BitUtils.HEXADECIMAL_BASE))

    def get_base_class(self):
        return (self.__int__() >> BitUtils.BITS_IN_BYTE) & BitUtils.LSB_TETRAD_MASK

    def get_sub_class(self):
        return self.__int__() & BitUtils.LSB_TETRAD_MASK

    # https://github.com/xiaoran007/pypci/blob/v0.0.4/src/pypci/backend/pci.py#L74
    def is_vga(self):
        return self.get_base_class() == self.BASE_CLASS_VGA or (
                self.get_base_class() == self.BASE_CLASS_BACKWARD_COMPATIBILITY and self.get_sub_class() == self.BASE_CLASS_BACKWARD_COMPATIBILITY_VGA)


# https://github.com/pciutils/pciutils/blob/master/pci.ids
class PciVendorId(int):
    INTEL = 0x8086

    def __new__(cls, vendor_id):
        return super(PciVendorId, cls).__new__(cls, BitUtils.get_int_with_check(vendor_id, bit_count=16, signed=False,
                                                                                base=BitUtils.HEXADECIMAL_BASE))

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


# https://en.wikipedia.org/wiki/PCI_configuration_space
# fixme utopia SR-IOV capability
# https://forums.servethehome.com/index.php?threads/quick-check-if-your-pcie-device-has-sr-iov-capability.39675/
class Pci:
    __ADDRESS = "address"  # [[[[<domain>]:]<bus>]:][<slot>][.[<func>]]
    __CLASS_NAME = "class_name"
    __CLASS_CODE = "class_code"
    __DEVICE_NAME = "device_name"
    __VENDOR_ID = "vendor_id"
    __DEVICE_ID = "device_id"
    __REVISION = "revision"
    __SUBSYSTEM_NAME = "subsystem_name"
    __SUBSYSTEM_VENDOR_ID = "subsystem_vendor_id"
    __SUBSYSTEM_ID = "subsystem_id"
    __IOMMU_GROUP = "iommu_group"
    __KERNEL_MODULE = "kernel_module"

    __REGEX_HEX8 = "[0-9a-fA-F]{2}"  # fixme utopia Использовать BitUtils.get_regex
    __REGEX_HEX16 = "[0-9a-fA-F]{4}"  # fixme utopia Использовать BitUtils.get_regex

    __REGEX = f"(?P<{__ADDRESS}>{__REGEX_HEX8}:{__REGEX_HEX8}\.\d+) (?P<{__CLASS_NAME}>.*) \[(?P<{__CLASS_CODE}>{PciClassCode.REGEX})\]: (?P<{__DEVICE_NAME}>.*) \[(?P<{__VENDOR_ID}>{__REGEX_HEX16}):(?P<{__DEVICE_ID}>{__REGEX_HEX16})\] \(rev (?P<{__REVISION}>{__REGEX_HEX8})\)|Subsystem: (?P<{__SUBSYSTEM_NAME}>.*) \[(?P<{__SUBSYSTEM_VENDOR_ID}>{__REGEX_HEX16}):(?P<{__SUBSYSTEM_ID}>{__REGEX_HEX16})\]|IOMMU group: (?P<{__IOMMU_GROUP}>[\d]+)|Kernel driver in use: (?P<{__KERNEL_MODULE}>.*)"

    # https://pkgs.org/search/?q=pciutils
    # https://man7.org/linux/man-pages/man8/lspci.8.html
    __CMD_LINE = "lspci -nnk -vvv"

    def __init__(self):
        self.address = ""
        self.class_name = ""
        self.class_code = PciClassCode(0)
        self.device_name = ""
        self.vendor_id = PciVendorId(0)
        self.device_id = 0
        self.revision = 0
        self.subsystem_name = ""
        self.subsystem_vendor_id = PciVendorId(0)
        self.subsystem_id = 0
        self.iommu_group = None
        self.kernel_module = ""

    def _init(self, pci):
        self.address = pci.address
        self.class_name = pci.class_name
        self.class_code = pci.class_code
        self.device_name = pci.device_name
        self.vendor_id = pci.vendor_id
        self.device_id = pci.device_id
        self.revision = pci.revision
        self.subsystem_name = pci.subsystem_name
        self.subsystem_vendor_id = pci.subsystem_vendor_id
        self.subsystem_id = pci.subsystem_id
        self.iommu_group = pci.iommu_group
        self.kernel_module = pci.kernel_module

    def __str__(self):
        return json.dumps({
            self.__ADDRESS: self.address,
            self.__CLASS_CODE: self.class_code,
            self.__DEVICE_NAME: self.class_name,
            self.__VENDOR_ID: self.vendor_id,
            self.__DEVICE_ID: self.device_id,
            self.__REVISION: self.revision,
            self.__SUBSYSTEM_NAME: self.subsystem_name,
            self.__SUBSYSTEM_VENDOR_ID: self.subsystem_vendor_id,
            self.__SUBSYSTEM_ID: self.subsystem_id,
            self.__IOMMU_GROUP: self.iommu_group,
            self.__KERNEL_MODULE: self.kernel_module
        })

    def __repr__(self):
        return self.__str__()

    def __setitem__(self, key, value):
        value_native = value
        if key == self.__CLASS_CODE:
            value_native = PciClassCode(value)
        elif key == self.__VENDOR_ID:
            value_native = PciVendorId(value)
        elif key == self.__DEVICE_ID:
            value_native = BitUtils.get_int_with_check(value, bit_count=16, signed=False,
                                                       base=BitUtils.HEXADECIMAL_BASE)
        elif key == self.__REVISION:
            value_native = BitUtils.get_int_with_check(value, bit_count=8, signed=False, base=BitUtils.HEXADECIMAL_BASE)
        elif key == self.__SUBSYSTEM_VENDOR_ID:
            value_native = PciVendorId(value)
        elif key == self.__SUBSYSTEM_ID:
            value_native = BitUtils.get_int_with_check(value, bit_count=16, signed=False,
                                                       base=BitUtils.HEXADECIMAL_BASE)
        elif key == self.__IOMMU_GROUP:
            value_native = BitUtils.get_int_with_check(value, bit_count=8, signed=False, base=BitUtils.DECIMAL_BASE)
        setattr(self, key, value_native)

    def __getitem__(self, key):
        return getattr(self, key)

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
        return f"{self.vendor_id:04x}:{self.device_id:04x}"

    def get_kernel_parameters(self):
        return []

    def get_vfio_pci_options_table(self):
        return {"multifunction": "on"}

    def get_qemu_parameters(self):
        return [VfioPci.get_device_for_passthrough(self)]

    class PciList(list):

        def __str__(self):
            return json.dumps(self, default=lambda o: o.__dict__)

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

        def get_iommu_group_list(self):
            result = set()
            for pci in self:
                if pci.iommu_group is not None:
                    result.add(pci.iommu_group)
            return result

        def get_pci_table_by_iommu_group(self):
            result = {}
            for pci in self:
                if pci.iommu_group in result:
                    result[pci.iommu_group].append(pci)
                else:
                    result.update({pci.iommu_group: Pci.PciList([pci])})
            return result

        def get_pci_list_by_iommu_group(self, iommu_group):
            pci_table_by_iommu_group = self.get_pci_table_by_iommu_group()
            if iommu_group in pci_table_by_iommu_group:
                return pci_table_by_iommu_group[iommu_group]
            return Pci.PciList()

        def get_vga_list(self):
            result = Pci.PciList()
            for pci in self:
                if pci.class_code.is_vga():
                    result.append(pci)
            return result

    @staticmethod
    def get_list():
        result = Pci.PciList()

        lspci_out = Pci.__run_lspci()

        for match in re.finditer(Pci.__REGEX, lspci_out, flags=re.MULTILINE):
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

    @staticmethod
    def get_device_for_passthrough(pci):
        # PCI устройство нельзя пробросить если оно не включено в iommu группу
        if pci.iommu_group is None:
            return {}

        vfio_pci_options_table = {"host": pci.address}
        vfio_pci_options_table.update(pci.get_vfio_pci_options_table())
        return {"-device": {"vfio-pci": vfio_pci_options_table}}

    def get_kernel_parameters(self):
        if len(self.__pci_list) == 0:
            return []
        return [{"vfio_pci.ids": pci.get_id() for pci in self.__pci_list}]

    def get_qemu_parameters(self):
        result = []
        for pci in self.__pci_list:
            result.extend(pci.get_qemu_parameters())
        return result


# https://docs.kernel.org/driver-api/vfio-mediated-device.html
# https://docs.kernel.org/driver-api/vfio.html
class Vfio:
    def __init__(self, vfio_pci):
        self.__vfio_pci = vfio_pci
        self.__iommu = Iommu()

    def get_kernel_parameters(self):
        result = [Vfio.__get_vfio(), Vfio.__get_mdev()]
        result.extend(self.__vfio_pci.get_kernel_parameters())
        result.extend(self.__iommu.get_kernel_parameters())
        return result

    @staticmethod
    def __get_vfio():
        return "vfio"

    @staticmethod
    def __get_mdev():  # fixme utopia Это нам требуется только для GVT-G (mediated) проброса GPU Intel
        return "mdev"


class VgaPciIntel(Pci):
    def __init__(self, pci):
        pass
        self._init(pci)

    # https://pve.proxmox.com/wiki/PCI_Passthrough#%22BAR_3:_can't_reserve_[mem]%22_error
    def get_kernel_parameters(self):  # module_blacklist=pci.kernel_module
        result = super().get_kernel_parameters()
        result.extend([{"i915.modeset": 0}, {"video": "efifb:off"}])
        return result

    def get_vfio_pci_options_table(self):
        result = super().get_vfio_pci_options_table()
        result.update({"display": "auto", "x-vga": "on", "x-igd-opregion": "on"})
        return result

    def get_qemu_parameters(self):
        result = super().get_qemu_parameters()
        if len(result) > 0:
            result.append({"-vga": "none"})
        return result

    @staticmethod
    def is_my_instance(pci):
        return pci.class_code.is_vga() and pci.vendor_id.is_intel()


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
    SLEEP_BEFORE_RECONNECT_SEC = 30
    SLEEP_AFTER_SERVER_START_SEC = 5

    def __init__(self):
        self.__open_vpn_config = OpenVpnConfig()

    def run(self):
        open_vpn_server_port = self.__open_vpn_config.get_server_port()

        my_ip_address_and_port = MyExternalIpAddressAndPort(open_vpn_server_port).get()

        TextConfigWriter(self.__open_vpn_config.get_my_current_ip_address_and_port()).set(
            my_ip_address_and_port)

        UDP_IP = my_ip_address_and_port.get_ip_address()
        UDP_PORT = my_ip_address_and_port.get_port()
        print("UDP target IP:", UDP_IP)
        print("UDP target port:", UDP_PORT)

        # sock_rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # sock_rx.bind((str("0.0.0.0"), open_vpn_server_port))

        udp_watchdog = UdpWatchdog(self.__open_vpn_config, my_ip_address_and_port)

        i = 0
        while True:
            udp_watchdog.watch()
            time.sleep(10)
            continue

            MESSAGE = f"test flush {i}"

            print("send message:", MESSAGE)

            sock_tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP
            sock_tx.sendto(bytes(MESSAGE, "utf-8"), (str(UDP_IP), UDP_PORT))

            # Receive data from the socket
            data, addr = sock_rx.recvfrom(1024)
            print(f"Received packet from {addr}: {data.decode('utf-8')}")

            i = i + 1
            time.sleep(5)
            continue

            self.__init()

            user_name = "utopia"
            user_ovpn_file_path = OpenVpnClientConfigGenerator(my_ip_address_and_port, user_name).generate()
            TelegramClient().send_file(user_ovpn_file_path)

            # fixme utopia Сгенерировать новые ovpn для всех клиентов и разослать их всем клиентам telegram бота
            #              список чатов видимо придётся копить в каком-то локальном конфиге, т.к. у телеграма нет такого метода в api

            try:  # fixme utopia Перепроверить что мы можем засечь разрыв соединения, к примеру, выключить WiFi
                # fixme utopia Нужно подкрутить какие-то настройки OpenVpn клиента
                # OpenVpnClient(watchdog_user_config_path).run()
                print("watchdog disable!")
                time.sleep(99999)
            except Exception as ex:
                print("Try udp hole punching and RECONNECT: {}".format(ex))

            # fixme utopia вырубить сервер

            time.sleep(self.SLEEP_BEFORE_RECONNECT_SEC)

    def __init(self):
        server_config_path = OpenVpnServerConfigGenerator().generate()
        OpenVpnServer(server_config_path).run()
        time.sleep(self.SLEEP_AFTER_SERVER_START_SEC)


class TcpPort:
    TCP_PORT_MIN = 1
    TCP_PORT_MAX = 65535

    SSH_PORT_DEFAULT = 22
    RDP_PORT_DEFAULT = 3389
    VNC_BASE_PORT_NUMBER = 5900

    def __init__(self, port):
        if not TcpPort.is_valid(port):
            raise Exception("TCP port FAIL: {}".format(port))
        self.__port = int(port)

    def __str__(self):
        return str(self.__port)

    def __repr__(self):
        return self.__str__()

    def __int__(self):
        return int(self.__port)

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
    RETRY_COUNT = 40

    def __init__(self, vm_meta_data, local_network_if, input_port, output_port):
        self.__vm_meta_data = vm_meta_data
        self.__local_network_if = NetworkInterface(local_network_if)
        self.__input_port = input_port
        self.__output_port = TcpPort(output_port)
        atexit.register(self.clear_at_exit)

    def add(self):
        if not self.__is_valid_input_port():
            print("TCP port forwarding DISCARDED")
            return
        print("TCP port forwarding for vm \"{}\": {}:{} --> {}".format(self.__vm_meta_data.get_name(),
                                                                       self.__local_network_if, self.__input_port,
                                                                       self.__get_vm_destination_ip_address_and_port()))
        self.__iptables_rule()

    def add_with_retry(self):
        sleep_sec = 5
        for i in range(VmTcpForwarding.RETRY_COUNT):
            try:
                print("{} Try TCP port forwarding".format(i + 1))
                self.add()
                print("TCP port forwarding OK")
                return
            except Exception as ex:
                print(ex)
                if i == VmTcpForwarding.RETRY_COUNT - 1:
                    print("TCP port forwarding ATTEMPTS OVER")
                    return
                time.sleep(sleep_sec)

    def clear(self):
        if not self.__is_valid_input_port():
            return
        self.__iptables_rule(clear=True)

    def clear_at_exit(self):
        try:
            self.clear()
        except Exception:
            return

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


class NoneFromString:
    __NONE_AS_STRING = {"null": None, "none": None}

    def __init__(self, target_string):
        self.__target_string = target_string.strip().lower()

    def get(self):
        if self.__target_string in self.__NONE_AS_STRING:
            return True, None

        return False, self.__target_string


class BoolFromString:
    __BOOL_AS_STRING = {"yes": True, "true": True, "on": True, "no": False, "false": False, "off": False}

    def __init__(self, target_string):
        self.__target_string = target_string.strip().lower()

    def get(self):
        if self.__target_string in self.__BOOL_AS_STRING:
            return True, self.__BOOL_AS_STRING[self.__target_string]

        return False, self.__target_string


class IntFromString:
    def __init__(self, target_string):
        self.__target_string = target_string.strip().lower()

    def get(self):
        return self.as_int()

    def as_int(self):
        is_good, result = self.as_decimal_int()
        if is_good:
            return is_good, result

        is_good, result = self.as_hexadecimal_int()
        if is_good:
            return is_good, result

        is_good, result = self.as_binary_int()
        if is_good:
            return is_good, result

        return self.as_octal_int()

    def as_decimal_int(self):
        if not BitUtils.is_decimal(self.__target_string):
            return False, self.__target_string
        return True, int(self.__target_string, BitUtils.DECIMAL_BASE)

    def as_hexadecimal_int(self):
        if not BitUtils.is_hexadecimal(self.__target_string):
            return False, self.__target_string
        return int(self.__target_string, BitUtils.HEXADECIMAL_BASE)

    def as_binary_int(self):
        if not BitUtils.is_binary(self.__target_string):
            return False, self.__target_string
        return int(self.__target_string, BitUtils.BINARY_BASE)

    def as_octal_int(self):
        if not BitUtils.is_octal(self.__target_string):
            return False, self.__target_string
        return int(self.__target_string, BitUtils.OCTAL_BASE)


class FloatFromString:
    def __init__(self, target_string):
        self.__target_string = target_string.strip().lower()

    def get(self):
        return self.as_float()

    def as_float(self):
        try:
            return True, float(self.__target_string)
        except:
            return False, self.__target_string


class NumberFromString:
    def __init__(self, target_string):
        self.__int_from_string = IntFromString(target_string)
        self.__float_from_string = FloatFromString(target_string)

    def get(self):
        is_good, result = self.__int_from_string.get()
        if is_good:
            return is_good, result

        return self.__float_from_string.get()


class StringFromString:
    def __init__(self, target_string, escape_literal=EscapeLiteral()):
        self.__target_string = target_string
        self.__escape_literal = escape_literal

    def get(self):
        if len(self.__target_string) == 0:
            return True, self.__target_string

        if (self.__target_string[0] == '"' and self.__target_string[-1] == '"') or (
                self.__target_string[0] == "'" and self.__target_string[-1] == "'"):
            self.__target_string = self.__target_string[1:-1]
            return True, self.__escape_literal.decode(self.__target_string)

        return False, self.__escape_literal.decode(self.__target_string)


class FromString:
    def get(self, target_string):
        if not isinstance(target_string, str):
            print(f"Parse NOT STRING: {target_string}")
            return target_string

        is_good, result_as_string = StringFromString(target_string).get()
        if is_good:
            print(f"Parse as string: {target_string} / {result_as_string}")
            return result_as_string

        is_good, result = NumberFromString(result_as_string).get()
        if is_good:
            print(f"Parse as number: {result} / {result_as_string}")
            return result

        is_good, result = BoolFromString(result_as_string).get()
        if is_good:
            print(f"Parse as bool: {result} / {result_as_string}")
            return result

        is_good, result = NoneFromString(result_as_string).get()
        if is_good:
            print(f"Parse as none: {result} / {result_as_string}")
            return result

        print(f"Parse UNKNOWN: {result_as_string}")

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

    def find_all(self, content, value_as_is=True):
        regex = re.compile(self.get_regex(), re.MULTILINE)
        tmp = regex.findall(content)
        result = dict()
        for groups in tmp:
            name = groups[0]
            value = ""
            for i in range(1 + self.__name_parser.get_subname_count_max(), len(groups)):
                value = groups[i]
                if len(value) > 0:
                    break
            result[name] = value if value_as_is else self.__from_string.get(value)
        return result

    def remove_by_name(self, name, content):
        empty_line = ""
        regex = re.compile(self.get_regex_for_remove_by_name(name), re.MULTILINE)
        content = regex.sub(empty_line, content)

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
    class EmptyValue:
        pass

    def normalize(self, config):
        result_normalize = dict()
        self.__normalize_recursive(config, result_normalize)
        result = []
        self.__normalize_recursive2(result_normalize, result)
        return result

    def __normalize_recursive(self, config, result_ref):
        if isinstance(config, dict):
            for key, value in config.items():
                if not key in result_ref:
                    result_ref[key] = dict()
                self.__normalize_recursive(value, result_ref[key])
        elif isinstance(config, list):
            for item in config:
                self.__normalize_recursive(item, result_ref)
        elif isinstance(config, str):  # Ключи без значений
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


class UnitTest_Normalizer(unittest.TestCase):
    def test_normalize(self):
        ref_table = [
            (
                [
                    "vfio",
                    {"vfio-pci": ["1", "2", "3", "4"]},
                    {"module-blacklist": ["i915", "kernel_module",
                                          "kernel_module2",
                                          "kernel_module3",
                                          "kernel_module4"]}, {"i915.modeset": "0"},
                    "mdev", {"iommu": "pt"}, {"intel_iommu": "on"}
                ],

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
            ),

            (
                [
                    {"key": {"subkey": ["value1", "value2"]}},
                    {"key2": [{"subkey2": {}}, {"subkey3": {}}]}
                ],

                {"key": [{"subkey": "value1"}, {"subkey": "value2"}, {"subkey": "value1"}],
                 "key2": {"subkey2": {}, "subkey3": []}}
            ),

            (
                ["key"],
                "key"
            )
        ]

        normalizer = Normalizer()
        for config_normalized, config in ref_table:
            result = normalizer.normalize(config)
            self.assertEqual(result, config_normalized, f"\n\nRESULT\n{result}\n\nREF\n{config_normalized}")


class LinuxKernelParamsSerializer(ShellSerializer):
    def __init__(self, key_modify_table=[("-", "_")]):
        super().__init__(key_value_separator_table=[
            {"prefix": "", "separator": "="}], nested_key_value_separator="=",
            nested_serializer=ShellSerializer(quotes_for_string_value="",
                                              key_value_separator_table=[
                                                  {"prefix": "", "separator": "?"}],
                                              pair_separator=","
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
            'vfio vfio_pci="1,2,3" module_blacklist="i915,kernel_module,kernel_module2,kernel_module3,kernel_module4" i915.modeset="0" mdev iommu="pt" intel_iommu="on"': [
                "vfio",
                {"vfio-pci": ["1", "2", "3"]},
                {"module-blacklist": ["i915", "kernel_module"]},
                {"module-blacklist": ["i915", "kernel_module2"]},
                {"module-blacklist": "kernel_module3"},
                {"module-blacklist": ["kernel_module4"]},
                {"module-blacklist": ["kernel_module3"]},
                {"i915.modeset": "0"},
                "mdev",
                {"iommu": "pt", "intel_iommu": "on"}
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
            result.update({name: FromString(value).get()})
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
            Power.__reboot_linux()
        elif CurrentOs.is_windows():
            Power.__reboot_windows()
        else:
            print("[Power] reboot not supported")

    @staticmethod
    def __reboot_linux():
        subprocess.check_call(["reboot"], shell=True)

    @staticmethod
    def __reboot_windows():
        subprocess.check_call(["shutdown", "/r", "/t", "0"], shell=True)


class Grub:
    GRUB_CMDLINE_LINUX = "GRUB_CMDLINE_LINUX"

    def __init__(self, grub_config_backup_path, grub_config_file_path=Path("/etc/default/grub")):
        self.__grub_config_reader = TextConfigReader(grub_config_file_path)
        self.__grub_config_writer = TextConfigWriter(grub_config_file_path,
                                                     last_backup_file_path=grub_config_backup_path)
        self.__linux_kernel_params_serializer = LinuxKernelParamsSerializer()
        self.__config_parser = ConfigParser()

    def update(self):
        print("[Grub] Update")
        subprocess.check_call(["update-grub"], shell=True)

    def append_cmd_line_linux(self, cmd_line_linux):
        grub_config = self.__grub_config_reader.get()

        grub_cmdline_linux = self.__config_parser.get_value(self.GRUB_CMDLINE_LINUX, grub_config)
        if grub_cmdline_linux is None:
            print(
                f"[Grub] {self.GRUB_CMDLINE_LINUX} parameter NOT FOUND in {self.__grub_config_reader}:\n{grub_config}")
            grub_cmdline_linux = ""

        # fixme utopia Прибавляем новые аргументы простой конкатенацией, т.к. в общем случае в GRUB_CMDLINE_LINUX могут
        #  находиться переменные ($VAR / ${VAR}) или вычислимые выражения (`command substitution` / $(command substitution)),
        #  т.к. конфигурация grub представляет собой bash файл
        #  Пытаться делать объединение через разбор параметров GRUB_CMDLINE_LINUX считаю нецелесообразным
        new_linux_kernel_params_serialized = grub_cmdline_linux + " " + self.__linux_kernel_params_serializer.serialize(
            cmd_line_linux)

        grub_config_modified = self.__config_parser.add_or_update(self.GRUB_CMDLINE_LINUX,
                                                                  new_linux_kernel_params_serialized,
                                                                  grub_config)

        print(f"[Grub] Config before:\n{grub_config}\n\nConfig after:\n{grub_config_modified}\n")
        return self.__grub_config_writer.set_with_backup(grub_config_modified)

    def restore_from_backup(self):
        print(f"[Grub] Restore from backup \"{self.__grub_config_writer.get_last_backup_file_path()}\"")
        return self.__grub_config_writer.restore_from_backup(is_remove_backup=True)


class StartupCrontab:
    COMMAND = "startup_run_all_scripts"
    SUPERVISOR_SCRIPT_ID = "073c0542-ab8f-4518-802b-4417a4519219"

    __STARTUP_SCRIPTS_DIR_NAME = ".crontab_startup_scripts"

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
        for path in sorted(pathlib.Path(self.__get_startup_script_dir().get()).glob("*"),
                           key=lambda x: x.stat().st_mtime_ns, reverse=True):
            if path.is_file():
                startup_script_name = StartupCrontab.StartupScriptName.parse(path.name)
                if startup_script_name is not None:
                    self.__run_startup_script(startup_script_name, path)

    def __register_supervisor_script(self):
        with CronTab(user=self.__user) as cron:
            command = f'"{sys.executable}" "{__file__}" {self.COMMAND}'
            if next(cron.find_comment(self.SUPERVISOR_SCRIPT_ID), None) is not None:
                return

            print(f"[Startup] register supervisor script: {command}")
            job = cron.new(command=command, comment=self.SUPERVISOR_SCRIPT_ID)
            job.every_reboot()

    def __create_startup_script_file(self, startup_script_name, startup_script_content):
        startup_script_file_path = self.__get_startup_script_file_path(startup_script_name)
        if self.__is_startup_script_file_exists(startup_script_name):
            print(f"[Startup] script {startup_script_file_path} ALREADY EXISTS")
            return False

        print(f"[Startup] Create script \"{startup_script_file_path}\":\n{startup_script_content}\n")
        TextConfigWriter(startup_script_file_path).set(startup_script_content, set_executable=True)
        return True

    def __run_startup_script(self, startup_script_name, startup_script_file_path):
        command = f'$("{startup_script_file_path}")'
        if startup_script_name.is_execute_once:
            command += f'; rm -f "{startup_script_file_path}"'
        if startup_script_name.is_background_executing:
            command += ' &'

        subprocess.run(command, shell=True, text=True)

    def __get_startup_script_file_path(self, startup_script_name):
        return self.__get_startup_script_dir().join(startup_script_name.get())

    def __is_startup_script_file_exists(self, startup_script_name):
        return self.__get_startup_script_dir().exists_by_wildcard(startup_script_name.get_wildcard())

    def __get_startup_script_dir(self):
        return Path.get_home_directory(self.__user).join(self.__STARTUP_SCRIPTS_DIR_NAME)


# Windows startup
# https://superuser.com/a/1518663/2121020
# fixme utopia Переопределить метод __register_supervisor_script() и __run_startup_script()
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


class VmRunner:
    def __init__(self, vm_name, project_config=OpenVpnConfig(), startup=Startup(), block_internet_access=False,
                 initiate_vga_pci_passthrough=False,
                 qemu_vga_pci_passthrough=None, grub_config_backup_path=None):
        self.__vm_name = vm_name
        self.__project_config = project_config
        self.__startup = startup
        self.__block_internet_access = bool(block_internet_access)
        self.__initiate_vga_pci_passthrough = bool(initiate_vga_pci_passthrough)
        self.__qemu_vga_pci_passthrough = qemu_vga_pci_passthrough
        self.__grub = Grub(grub_config_backup_path=grub_config_backup_path)
        self.__serializer = ShellSerializer()

    def run(self):
        if self.__initiate_vga_pci_passthrough:
            if self.__qemu_vga_pci_passthrough:
                self.after_reboot()
            else:
                self.before_reboot()
        else:
            self.__run()

    def before_reboot(self):
        pci_list = Pci.get_list()

        pci_vga_list = pci_list.get_vga_list()
        if len(pci_vga_list) == 0:
            Logger.instance().error("[Vm] PCI VGA NOT FOUND")
            return

        if len(pci_vga_list) > 1:
            Logger.instance().error("[Vm] Multiple VGA FOUND")  # fixme utopia Дать выбрать какой VGA пробрасывать
            return

        iommu_group = pci_vga_list[0].iommu_group

        if iommu_group is None:
            Logger.instance().error("[Vm] VGA does not include to iommu group")
            return

        pci_list_by_vga_iommu_group = pci_list.get_pci_list_by_iommu_group(iommu_group)

        vfio_pci = VfioPci(pci_list_by_vga_iommu_group)
        vfio = Vfio(vfio_pci)

        grub_config_backup_path = self.__grub.append_cmd_line_linux(vfio.get_kernel_parameters())
        if grub_config_backup_path is None:
            Logger.instance().error("[Vm] Make grub config backup FAIL")
            return
        self.__grub.update()

        command_line = f'"{sys.executable}" "{__file__}" {self.__serializer.serialize(["vm_run", [self.__vm_name, "--bi" if self.__block_internet_access else "", {"--QemuVgaPciPassthrough": str(QemuVgaPciPassthrough(vfio_pci)), "--grub_config_backup_path": str(grub_config_backup_path)}, "--pp" if self.__initiate_vga_pci_passthrough else ""]])}'

        self.__startup.register_script(command_line, is_background_executing=True, is_execute_once=True)
        # Power.reboot()

    def after_reboot(self):
        try:
            self.__run()
        finally:
            self.__grub.restore_from_backup()
            self.__grub.update()
            # Power.reboot()

    def __run(self):
        network_bridge = NetworkBridge(self.__project_config.get_server_name(),
                                       self.__project_config.get_vm_bridge_ip_address_and_mask(),
                                       self.__project_config.get_dns_config_dir(),
                                       self.__project_config.get_internet_network_interface(),
                                       block_internet_access=self.__block_internet_access)

        vm_registry = VmRegistry(self.__project_config.get_vm_registry_path())
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

        virtio = Virtio(self.__project_config)
        vm = VirtualMachine(network_bridge, vm_meta_data, virtio=virtio, qemu_vga=self.__qemu_vga_pci_passthrough)
        vm.run()
        tcp_forwarding_thread.join()


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
        super().__init__()
        self.__vm_meta_data = vm_meta_data
        self.__is_tpm2_0 = is_tpm2_0
        self.__log_level = log_level
        self.__serializer = TpmEmulator.TpmSerializer()

    def get_qemu_parameters(self):
        self.__get_tpm_state_dir_path().makedirs()
        return [{"-chardev": {"socket": {"id": self.__get_tpm_chardev_id(),
                                         "path": self.__get_tpm_chardev_ctrl_unixsocket_path()}}},
                {"-tpmdev": {
                    "emulator": {"id": self.__get_tpm_dev_id(), "chardev": self.__get_tpm_chardev_id()}}},

                {"-device": {
                    self.__get_tpm_dev_model(): {"tpmdev": self.__get_tpm_dev_id()}}}
                ]

    def _start_impl(self):
        self.__get_tpm_state_dir_path().makedirs()

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
        return self.__get_tpm_state_dir_path().join(self.__get_tpm_chardev_ctrl_unixsocket_name())

    def __get_tpm_log_file_path(self):
        return self.__get_tpm_state_dir_path().join(f"{self.PREFIX}.log")

    def __get_tpm_state_dir_path(self):
        return self.__vm_meta_data.get_working_dir_path().join(self.PREFIX)

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
        self.__get_serial_state_dir_path().makedirs()
        return [{"-chardev": {
            "stdio": {"id": self.__get_serial_chardev_id(), "mux": "on", "logfile": self.__get_serial_log_file_path(),
                      "signal": "off"}}}, {"-serial": f"chardev:{self.__get_serial_chardev_id()}"}]

    def __get_serial_chardev_id(self):
        return f"{self.PREFIX}-{self.__vm_meta_data.get_name()}-chardev-id{self.__index}"

    def __get_serial_log_file_path(self):
        return self.__get_serial_state_dir_path().join(f"{self.PREFIX}.log")

    def __get_serial_state_dir_path(self):
        return self.__vm_meta_data.get_working_dir_path().join(f"{self.PREFIX}{self.__index}")


class QemuLogging:
    PREFIX = "qemu"

    def __init__(self, vm_meta_data):
        self.__vm_meta_data = vm_meta_data

    def get_qemu_parameters(self):
        self.__get_qemu_state_dir_path().makedirs()
        return [{"-D": self.__get_qemu_log_file_path()}]

    def __get_qemu_log_file_path(self):
        return self.__get_qemu_state_dir_path().join(f"{self.PREFIX}.log")

    def __get_qemu_state_dir_path(self):
        return self.__vm_meta_data.get_working_dir_path().join(self.PREFIX)


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
        return self.__vm_meta_data.get_working_dir_path().join(self.PREFIX)


class QemuBios:
    # SeaBIOS используется по умолчанию, дополнительные аргументы не требуются
    def get_qemu_parameters(self):
        return []


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


class QemuVgaPciPassthrough:
    def __init__(self, vfio_pci):
        if isinstance(vfio_pci, VfioPci):
            self.__vfio_pci = vfio_pci
        elif isinstance(vfio_pci, str):
            self.__vfio_pci = VfioPci.from_string(vfio_pci)
        else:
            raise Exception(f"[QemuVgaPciPassthrough] vfio_pci TYPE MISMATCH: {type(vfio_pci)}")

    def __str__(self):
        return str(self.__vfio_pci)

    def __repr__(self):
        return self.__str__()

    def get_qemu_parameters(self):
        return self.__vfio_pci.get_qemu_parameters()


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
                 vm_meta_data=VmMetaData("disk1", "/opt/share/disk1.img", "00:12:35:56:78:9a"),
                 path_to_iso_installer=None, virtio=None, tpm=None, qemu_serial=None, qemu_logging=None,
                 qemu_bios=None, qemu_vga=None):
        self.__tap = Tap()
        self.__network_bridge = network_bridge
        self.__vm_meta_data = vm_meta_data
        self.__path_to_iso_installer = path_to_iso_installer
        self.__virtio = virtio
        self.__tpm = TpmEmulator(vm_meta_data) if tpm is None else tpm
        self.__qemu_serial = QemuSerial(vm_meta_data) if qemu_serial is None else qemu_serial
        self.__qemu_logging = QemuLogging(vm_meta_data) if qemu_logging is None else qemu_logging
        self.__qemu_bios = QemuUefi(vm_meta_data) if qemu_bios is None else qemu_bios
        self.__qemu_vga = QemuVgaVirtio() if qemu_vga is None else qemu_vga
        self.__serializer = QemuSerializer()

    def run(self):
        self.__network_bridge.create()
        self.__tpm.start()

        command_line = self.__command_line()
        Logger.instance().debug(f"[Vm] {command_line}")
        subprocess.check_call(command_line, shell=True)
        self.__tpm.close()

    def __command_line(self):
        command_parts_list = [self.__qemu_command_line(), self.__kvm_enable(), self.__ram_size(),
                              self.__network(),
                              self.__other(), self.__disk(), self.__iso_installer(), self.__virtio_win_drivers(),
                              self.__cpu(), self.__get_qemu_vga_command_line(), self.__usb(), self.__monitor(),
                              self.__get_qemu_bios_command_line(),
                              self.__get_tpm_command_line(), self.__get_qemu_serial_command_line(),
                              self.__get_qemu_logging_command_line()]
        return " ".join(command_parts_list)

    @staticmethod
    def __qemu_command_line():
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
        return "-m 8192"

    def __network(self):
        self.__tap.create()
        self.__network_bridge.add_and_configure_tap(self.__tap, self.__vm_meta_data)

        tap_name = str(self.__tap)
        netdev_id = "{}-id".format(tap_name)

        # fixme utopia Присвоим ip адрес vm через mac адрес
        # https://superuser.com/questions/1413011/setting-a-static-ip-upon-qemu-vm-creation

        return "-netdev tap,ifname={0},script=no,downscript=no,id={1} -device virtio-net,netdev={1},mac={2}".format(
            tap_name, netdev_id, self.__vm_meta_data.get_mac_address_as_string())

    def __disk(self):
        return "-drive file=\"{}\",media=disk,if=virtio".format(self.__vm_meta_data.get_image_path())

    def __iso_installer(self):
        if self.__path_to_iso_installer is None:
            return ""
        return "-cdrom \"{}\"".format(self.__path_to_iso_installer)

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
        # CPU который поддерживается Windows 11
        return "-cpu Icelake-Server-v5 -smp 4,sockets=1,cores=2,threads=2,maxcpus=4"

    def __get_qemu_vga_command_line(self):
        return self.__serializer.serialize(self.__qemu_vga.get_qemu_parameters())

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

    def __virtio_win_drivers(self):
        if self.__virtio is None:
            return ""
        return "-drive file=\"{}\",media=cdrom,if=ide".format(self.__virtio.get_win_drivers())

    def __get_tpm_command_line(self):
        return self.__serializer.serialize(self.__tpm.get_qemu_parameters())

    def __get_qemu_serial_command_line(self):
        return self.__serializer.serialize(self.__qemu_serial.get_qemu_parameters())

    def __get_qemu_logging_command_line(self):
        return self.__serializer.serialize(self.__qemu_logging.get_qemu_parameters())

    def __get_qemu_bios_command_line(self):
        return self.__serializer.serialize(self.__qemu_bios.get_qemu_parameters())


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

    parser_vm_install = subparsers.add_parser("vm_install", help="Install OS on virtual machine")
    parser_vm_install.add_argument("vm_name", type=str, help="Virtual machine name")
    parser_vm_install.add_argument("os_distr_path", type=Path, help="OS distributive iso image path")
    parser_vm_install.add_argument("--bi", help="Block internet access, but not the local network",
                                   action='store_true')

    parser_vm_run = subparsers.add_parser("vm_run", help="Run virtual machine")
    parser_vm_run.add_argument("vm_name", type=str, help="Virtual machine name")
    parser_vm_run.add_argument("--bi", help="Block internet access, but not the local network",
                               action='store_true')
    parser_vm_run.add_argument("--pp", help="Initiate VGA PCI passthrough to virtual machine",
                               action='store_true')
    parser_vm_run.add_argument("--QemuVgaPciPassthrough", type=QemuVgaPciPassthrough,
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
        Daemon().run()

    elif args.command == "check":
        MyExternalIpAddressAndPort(project_config.get_server_port()).get()

    elif args.command == "user_ovpn":
        my_ip_address_and_port = IpAddressAndPort(
            TextConfigReader(project_config.get_my_current_ip_address_and_port()).get())
        print(OpenVpnClientConfigGenerator(my_ip_address_and_port, args.user_name).generate())

    elif args.command == "vm_create":
        print(VmRegistry(project_config.get_vm_registry_path()).create(args.vm_name, args.image_size).get_image_path())

    elif args.command == "vm_install":
        if not args.os_distr_path.exists():
            raise Exception("OS distributive image \"{}\" NOT FOUND".format(args.os_distr_path))

        local_network_interface = OpenVpnConfig.get_or_default_local_network_interface(
            project_config.get_local_network_interface())

        network_bridge = NetworkBridge(project_config.get_server_name(),
                                       project_config.get_vm_bridge_ip_address_and_mask(),
                                       project_config.get_dns_config_dir(), local_network_interface,
                                       block_internet_access=args.bi)

        vm_registry = VmRegistry(project_config.get_vm_registry_path())
        vm_meta_data = vm_registry.get_with_verifying(args.vm_name)
        virtio = Virtio(project_config)
        vm = VirtualMachine(network_bridge, vm_meta_data, args.os_distr_path, virtio=virtio)
        vm.run()

    elif args.command == "vm_run":
        VmRunner(args.vm_name, project_config=project_config, block_internet_access=args.bi,
                 initiate_vga_pci_passthrough=args.pp, qemu_vga_pci_passthrough=args.QemuVgaPciPassthrough,
                 grub_config_backup_path=args.grub_config_backup_path).run()

    elif args.command == "vm_ssh_fwd":
        vm_registry = VmRegistry(project_config.get_vm_registry_path())
        vm_registry.set_ssh_forward_port(args.vm_name, args.host_tcp_port)

    elif args.command == "vm_rdp_fwd":
        vm_registry = VmRegistry(project_config.get_vm_registry_path())
        vm_registry.set_rdp_forward_port(args.vm_name, args.host_tcp_port)

    elif args.command == "test":
        Logger.instance().error("FFFF")
        # ggg = ConfigParser().find_all(TextConfigReader("/etc/default/grub").get())
        # print(ggg)
        # print(LinuxKernelParamsParser().find_all(ggg["GRUB_CMDLINE_LINUX"]))


    elif args.command == StartupCrontab.COMMAND:
        Startup().run_all_scripts()


if __name__ == '__main__':
    main()
