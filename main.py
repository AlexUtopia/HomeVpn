import atexit
import os.path
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
import randmac

# fixme utopia Исправление для iptc который неадекватно работает на Ubuntu 22.04
os.environ['XTABLES_LIBDIR'] = "/usr/lib/x86_64-linux-gnu/xtables/"

import psutil
import stun
import iptc
import socket
import platform


# https://tproger.ru/translations/demystifying-decorators-in-python/


class Path:
    def __init__(self, path):
        self.__path = os.path.expanduser(os.path.expandvars(str(path)))

    def get(self):
        if os.path.isabs(self.__path):
            return self.__path
        this_script_dir = os.path.dirname(os.path.realpath(__file__))
        result = os.path.abspath(os.path.join(this_script_dir, self.__path))
        return result

    def exists(self):
        return os.path.exists(self.get())

    def makedirs(self):
        path = self.get()
        if os.path.isfile(path):
            raise Exception("Path \"{}\" is path to file, but should be a directory path".format(path))
        if os.path.isdir(path):
            # print("[WARNING] Path \"{}\" is path to exists directory".format(path))
            return
        os.makedirs(path)

    def __str__(self):
        return self.get()

    def __repr__(self):
        return self.__str__()


class TextConfigReader:
    def __init__(self, config_file_path, encoding="utf-8"):
        self.__config_file_path = Path(config_file_path)
        self.__encoding = str(encoding)

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
    def __init__(self, config_file_path, encoding="utf-8"):
        self.__config_file_path = Path(config_file_path)
        self.__encoding = str(encoding)

    def set(self, data):
        self.__makedirs()

        with open(self.__config_file_path.get(), mode="wt", encoding=self.__encoding) as config_file:
            config_file.write(str(data))
        return self.__config_file_path

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
        print(
            "NAT type: {}\nUDP hole punching: {}".format(nat_type, self.__nat_adapted_for_udp_hole_punching(nat_type)))
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
        print("STUN server: {}:{}".format(hostname, port))
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
        print("OpenVpn server return: {}".format(result))

        if result.returncode:
            raise Exception("OpenVpn server start FAIL: {}".format(result.stderr))

        print("OpenVpn server start OK")


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
        print("OpenVpn client return: {}".format(result))

        if result.returncode:
            raise Exception("OpenVpn client start FAIL: {}".format(result.stderr))

        print("OpenVpn client start OK")


class TelegramBotConfig(JsonConfigReader):
    def __init__(self, config_file_path="telegram-bot.config.json"):
        super().__init__(config_file_path)

    pass


class TelegramClient:
    ENCODING = "utf-8"

    def __init__(self):
        self.__config = TelegramBotConfig().get()

    def send_message(self, message):
        with urllib.request.urlopen(self.__get_send_message_url(), self.__get_data(message)) as f:
            print("Telegram send message: {}".format(f.read().decode(self.ENCODING)))

    def __get_send_message_url(self):
        return self.__get_url("sendMessage")

    def __get_url(self, command):
        return "https://api.telegram.org/bot{}/{}".format(self.__config["bot_token"], command)

    def __get_data(self, message):
        data = urllib.parse.urlencode({"chat_id": self.__config["chat_id"], "text": message})
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

    def get_watchdog_user_name(self):
        return self.get_config_parameter_strong("watchdog_user_name")

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
        # self.__add_client_route_to_vm_bridge_network()

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
        self.__key_value_config.add("push", "route {} {}".format(ip_network.network_address, ip_network.netmask))


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

    def __init__(self, bridge_if, internet_if):
        if bridge_if is None or not bridge_if.exists():
            raise Exception("Bridge interface NOT FOUND")

        if internet_if is None or not internet_if.exists():
            raise Exception("Internet interface NOT FOUND")

        self.__bridge_name = str(bridge_if)
        self.__internet_if_name = str(internet_if)

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
        rule.out_interface = self.__internet_if_name
        target = iptc.Target(rule, "ACCEPT")
        rule.target = target

        if clear:
            chain.delete_rule(rule)
        else:
            chain.insert_rule(rule)
        table.commit()

    def __setup_nat_postrouting_masquerade(self, clear=False):
        # sudo iptables -t nat -A POSTROUTING -o {self.__internet_if_name} -j MASQUERADE
        # sudo iptables -t nat -L -v -n

        table = iptc.Table(iptc.Table.NAT)
        chain = iptc.Chain(table, "POSTROUTING")

        rule = iptc.Rule()
        rule.out_interface = self.__internet_if_name
        target = iptc.Target(rule, "MASQUERADE")
        rule.target = target

        if clear:
            chain.delete_rule(rule)
        else:
            chain.insert_rule(rule)
        table.commit()

    def __setup_filter_internet_to_bridge(self, clear=False):
        # sudo iptables -t filter -A FORWARD -i {self.__internet_if_name} -o {self.__bridge_name} -m state --state RELATED,ESTABLISHED -j ACCEPT
        # sudo iptables -t filter -L -v -n

        table = iptc.Table(iptc.Table.FILTER)
        chain = iptc.Chain(table, "FORWARD")

        rule = iptc.Rule()
        rule.in_interface = self.__internet_if_name
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


# https://en.wikipedia.org/wiki/Hostname
# Название должно полностью подчиняться правилам формирования host имени
# tolower case
# без точек в имени dnsmasq их не понимает https://serverfault.com/a/229349
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
                 dhcp_host_dir="./dhcp-hostsdir", internet_network_interface=None):
        self.__interface = NetworkInterface("{}-bridge".format(name))
        self.__bridge_ip_address_and_mask = ipaddress.ip_interface(bridge_ip_address_and_mask)

        if internet_network_interface is not None:
            self.__internet_network_interface = NetworkInterface(internet_network_interface)
            print("Internet network interface SET MANUALLY: {}".format(self.__internet_network_interface))
        else:
            self.__internet_network_interface = None

        self.__dns_dhcp_provider = DnsDhcpProvider(self.__interface, dhcp_host_dir)
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
        BridgeFirewall(self.__interface, self.__internet_network_interface).setup()

    def __clear_firewall(self):
        try:
            BridgeFirewall(self.__interface, self.__internet_network_interface).clear_at_exit()
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


class VirtualMachine:
    def __init__(self, network_bridge,
                 vm_meta_data=VmMetaData("disk1", "/opt/share/disk1.img", "00:12:35:56:78:9a"),
                 path_to_iso_installer=None, virtio=None):
        self.__tap = Tap()
        self.__network_bridge = network_bridge
        self.__vm_meta_data = vm_meta_data
        self.__path_to_iso_installer = path_to_iso_installer
        self.__virtio = virtio

    def run(self):
        self.__network_bridge.create()

        command_line = self.__command_line()
        print(command_line)
        subprocess.check_call(command_line, shell=True)

    def __command_line(self):
        command_parts_list = [self.__qemu_command_line(), self.__kvm_enable(), self.__ram_size(),
                              self.__network(),
                              self.__other(), self.__disk(), self.__iso_installer(), self.__virtio_win_drivers(),
                              self.__cpu(), self.__gpu(), self.__usb()]
        return " ".join(command_parts_list)

    @staticmethod
    def __qemu_command_line():
        return "qemu-system-{}".format(platform.machine())

    @staticmethod
    def __kvm_enable():
        return "-enable-kvm"

    @staticmethod
    def __ram_size():  # fixme utopia Использовать psutil
        return "-m 16384"

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
        # -cdrom ~/Загрузки/linuxmint-20.2-cinnamon-64bit.iso
        # -vga std -vnc 127.0.0.1:2
        # -bt hci,host:hci0
        # https://qemu-project.gitlab.io/qemu/system/devices/usb.html
        # https://www.youtube.com/watch?v=ELbxhm1-rno
        # -full-screen
        # -device virtio-vga-gl -display sdl,gl=on
        # /usr/share/ovmf/OVMF.fd
        return "-vnc 127.0.0.1:2 -bios /usr/share/OVMF/OVMF_CODE.fd"

    def __cpu(self):
        return "-cpu host -smp 8,sockets=1,cores=4,threads=2,maxcpus=8"

    def __gpu(self):
        # return "-vga std -display gtk"

        # return "-device virtio-vga-gl -display sdl,gl=on"

        # return "-nographic"

        # https://www.reddit.com/r/VFIO/comments/cktnhv/bar_0_cant_reserve/
        # https://listman.redhat.com/archives/vfio-users/2016-March/msg00088.html
        # ,display=auto,multifunction=on,x-vga=on,
        # x-igd-opregion=on,
        return "-vga none -device vfio-pci,host=00:02.0,romfile=\"/home/utopia/Загрузки/Release/i915ovmf.rom\""

    def __usb(self):
        usb_device_array = [
            (0x045e, 0x00db),  # Клавиатура Microsoft # Natural Ergonomic Keyboard 4000 v 1.0
            (0x0bda, 0x8771),  # USB-Bluetooth 5.0 адаптер Ugreen # CM390
            (0x046d, 0xc05b)  # Мышка Logitec # B110
        ]

        result = []

        for vid, pid in usb_device_array:
            result.append("-usb -device usb-host,vendorid=0x{:04X},productid=0x{:04X}".format(vid, pid))

        return " ".join(result)

    def __virtio_win_drivers(self):
        if self.__virtio is None:
            return ""
        return "-drive file=\"{}\",media=cdrom,if=ide".format(self.__virtio.get_win_drivers())


class Daemon:
    SLEEP_BEFORE_RECONNECT_SEC = 30
    SLEEP_AFTER_SERVER_START_SEC = 5

    def __init__(self):
        self.__open_vpn_config = OpenVpnConfig()

    def run(self):
        open_vpn_server_port = self.__open_vpn_config.get_server_port()

        while True:
            my_ip_address_and_port = MyExternalIpAddressAndPort(open_vpn_server_port).get()

            TextConfigWriter(self.__open_vpn_config.get_my_current_ip_address_and_port()).set(
                my_ip_address_and_port)

            self.__init()

            TelegramClient().send_message(
                "Хорошего дня, лови новые параметры подключения\nIP Address: {}\nPort: {}".format(
                    my_ip_address_and_port.get_ip_address(), my_ip_address_and_port.get_port()))

            watchdog_user_name = self.__open_vpn_config.get_watchdog_user_name()
            watchdog_user_config_path = OpenVpnClientConfigGenerator(my_ip_address_and_port,
                                                                     watchdog_user_name).generate()

            # fixme utopia Сгенерировать новые ovpn для всех клиентов и разослать их всем клиентам telegram бота
            #              список чатов видимо придётся копить в каком-то локальном конфиге, т.к. у телеграма нет такого метода в api

            try:  # fixme utopia Перепроверить что мы можем засечь разрыв соединения, к примеру, выключить WiFi
                # fixme utopia Нужно подкрутить какие-то настройки OpenVpn клиента
                OpenVpnClient(watchdog_user_config_path).run()
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
    RETRY_COUNT = 4

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


class RegexConstants:
    INT64_DECIMAL_DIGITS_COUNT = 19
    CAPTURE_ALL = fr"(.*)"
    SPACE_SYMBOLS = fr"[\t ]"
    SPACE_SYMBOLS_ZERO_OR_MORE = fr"{SPACE_SYMBOLS}*"
    SPACE_SYMBOLS_ONE_OR_MORE = fr"{SPACE_SYMBOLS}+"
    INT64_INTEGER_WITHOUT_SING = fr"[0-9]{{1,{INT64_DECIMAL_DIGITS_COUNT}}}"
    INT64_INTEGER = fr"{INT64_INTEGER_WITHOUT_SING}|\+{INT64_INTEGER_WITHOUT_SING}|-{INT64_INTEGER_WITHOUT_SING}"


class EscapeLiteral:
    __ESCAPE = [("\\\\", "\\"), ("\\\"", "\""), ("\\\'", "'"), ("\\\n", ""), ("\\\r", ""), ("\\\r\n", ""),
                ("\\\n\r", "")]

    def __init__(self, target_string):
        self.__target_string = target_string

    def escape(self):
        result = ""
        for escape_literal, replace_literal in self.__ESCAPE:
            result = self.__target_string.replace(escape_literal, replace_literal)
        return result


class BoolFromString:
    __BOOL_AS_STRING = {"yes": True, "true": True, "1": True, "no": False, "false": False, "0": False}

    def __init__(self, target_string):
        self.__target_string = target_string

    def get(self, default_value=False):
        result = self.get_or_none()
        if result is not None:
            return result

        return default_value

    def is_bool(self):
        return self.get_or_none() is not None

    def get_or_none(self):
        target_string_trimmed = self.__target_string.strip().lower()
        return self.__BOOL_AS_STRING.get(target_string_trimmed, None)


class IntFromString:
    __DECIMAL_BASE = 10
    __HEXADECIMAL_BASE = 16
    __BINARY_BASE = 2
    __OCTAL_BASE = 8

    def __init__(self, target_string):
        self.__target_string = target_string

    def get(self):
        return self.as_int()

    def is_int(self):
        return self.as_int() is not None

    def as_int(self):
        result = self.as_decimal_int()
        if result is not None:
            return result

        result = self.as_hexadecimal_int()
        if result is not None:
            return result

        result = self.as_binary_int()
        if result is not None:
            return result

        return self.as_octal_int()

    def is_decimal_int(self):
        return self.as_decimal_int() is not None

    def as_decimal_int(self):
        try:
            return int(self.__target_string, self.__DECIMAL_BASE)
        except:
            return None

    def is_hexadecimal_int(self):
        return self.as_hexadecimal_int() is not None

    def as_hexadecimal_int(self):
        try:
            return int(self.__target_string, self.__HEXADECIMAL_BASE)
        except:
            return None

    def is_binary_int(self):
        return self.as_binary_int() is not None

    def as_binary_int(self):
        try:
            return int(self.__target_string, self.__BINARY_BASE)
        except:
            return None

    def is_octal_int(self):
        return self.as_octal_int() is not None

    def as_octal_int(self):
        try:
            return int(self.__target_string, self.__OCTAL_BASE)
        except:
            return None


class FloatFromString:
    def __init__(self, target_string):
        self.__target_string = target_string

    def get(self):
        return self.as_float()

    def is_float(self):
        return self.as_float() is not None

    def as_float(self):
        try:
            return float(self.__target_string)
        except:
            return None


class NumberFromString:
    def __init__(self, target_string):
        self.__int_from_string = IntFromString(target_string)
        self.__float_from_string = FloatFromString(target_string)

    def is_number(self):
        return self.get() is not None

    def get(self):
        result = self.__int_from_string.get()
        if result is not None:
            return result

        return self.__float_from_string.get()


class StringFromString:
    __REGEX_STRING_DOUBLE_QUOTES = fr"^\"{RegexConstants.CAPTURE_ALL}\""
    __REGEX_STRING_SINGLE_QUOTES = fr"^'{RegexConstants.CAPTURE_ALL}'"
    __REGEX = fr"{__REGEX_STRING_DOUBLE_QUOTES}|{__REGEX_STRING_SINGLE_QUOTES}|{RegexConstants.CAPTURE_ALL}"

    def __init__(self, target_string):
        self.__target_string = target_string

    def get(self):
        regex = re.compile(self.__REGEX)
        result = regex.search(self.__target_string).group(0)
        return EscapeLiteral(result).escape()


class FromString:
    def get(self, target_string):
        value_as_string = StringFromString(target_string).get()
        if value_as_string is not str:
            return value_as_string

        result = NumberFromString(value_as_string).get()
        if result is not None:
            return result

        result = BoolFromString(value_as_string).get()
        if result is not None:
            return result

        return value_as_string


class ConfigParameterNameParser:
    __NAME_LENGTH_MAX = 64

    def get_regex(self):
        return fr"^([a-zA-Z_][\w]{{0,{self.__NAME_LENGTH_MAX - 1}}})"

    def get_regex_for_name(self, name):
        return fr"^{name}"


class ConfigNameValueDelimiterParser:
    def get_regex(self):
        return fr"="


class ConfigParameterValueParser:
    __DOUBLE_QUOTE = "\""
    __SINGLE_QUOTE = "'"
    __BACK_SLASH_ESCAPE = fr"\\"
    __DOUBLE_QUOTE_ESCAPE = fr"{__BACK_SLASH_ESCAPE}{__DOUBLE_QUOTE}"
    __SINGLE_QUOTE_ESCAPE = fr"{__BACK_SLASH_ESCAPE}{__SINGLE_QUOTE}"

    def get_regex(self, with_capture=True):
        regex_with_double_quote = self.__get_regex_with_quotes(self.__DOUBLE_QUOTE, self.__DOUBLE_QUOTE_ESCAPE,
                                                               with_capture)
        regex_with_single_quote = self.__get_regex_with_quotes(self.__SINGLE_QUOTE, self.__SINGLE_QUOTE_ESCAPE,
                                                               with_capture)
        regex_simple = self.__get_regex_simple(with_capture)
        return fr"{regex_with_double_quote}|{regex_with_single_quote}|{regex_simple}"

    def __get_regex_with_quotes(self, quote, quote_escape, with_capture):
        begin_mark = quote
        end_mark = quote
        unacceptable_symbols = quote
        escape = quote_escape
        return self.__get_regex_template(begin_mark, end_mark, unacceptable_symbols, escape, with_capture)

    def __get_regex_simple(self, with_capture):
        begin_mark = ""
        end_mark = ""
        unacceptable_symbols = fr"\s{self.__DOUBLE_QUOTE}{self.__SINGLE_QUOTE}"
        escape = fr"{self.__DOUBLE_QUOTE_ESCAPE}|{self.__SINGLE_QUOTE_ESCAPE}"
        return self.__get_regex_template(begin_mark, end_mark, unacceptable_symbols, escape, with_capture)

    def __get_regex_template(self, begin_mark, end_mark, unacceptable_symbols, escape, with_capture):
        back_slash_escape = self.__BACK_SLASH_ESCAPE

        begin_capture = ""
        end_capture = ""
        if bool(with_capture):
            begin_capture = "("
            end_capture = ")"
        return rf"{begin_capture}{begin_mark}(?:[^{unacceptable_symbols}]*(?:{back_slash_escape}|{escape})*)*{end_mark}{end_capture}{RegexConstants.SPACE_SYMBOLS}*$"


class ConfigParser:
    def __init__(self, name_parser=ConfigParameterNameParser(), delimiter_parser=ConfigNameValueDelimiterParser(),
                 value_parser=ConfigParameterValueParser(), from_string=FromString()):
        self.__name_parser = name_parser
        self.__delimiter_parser = delimiter_parser
        self.__value_parser = value_parser
        self.__from_string = from_string

    def get_value(self, name, content):
        return self.__from_string.get(self.get_value_as_is(name, content))

    def get_value_as_is(self, name, content):
        regex = re.compile(self.get_regex_for_search_value_by_name(name), re.MULTILINE)
        regex_result = regex.search(content)
        if regex_result is None:
            return None

        return regex_result.group(0)

    def find_all(self, content):
        regex = re.compile(self.get_regex(), re.MULTILINE)
        tmp = regex.findall(content)

        result = dict()
        for name, value in tmp:
            result.update({name: self.__from_string.get(value)})
        return result

    def remove_by_name(self, name, content):
        empty_line = ""
        regex = re.compile(self.get_regex_for_remove_by_name(name), re.MULTILINE)
        content = regex.sub(empty_line, content)

    def add_or_update(self, name, content):
        print(name)

    def get_regex(self):
        return self.__get_regex_template(self.__name_parser.get_regex())

    def get_regex_for_search_value_by_name(self, name):
        return self.__get_regex_template(self.__name_parser.get_regex_for_name(name))

    def get_regex_for_remove_by_name(self, name):
        result = self.__get_regex_template(self.__name_parser.get_regex_for_name(name), with_value_capture=False)
        return fr"({result})"

    def __get_regex_template(self, name_template, with_value_capture=True):
        return fr"{name_template}{self.__delimiter_parser.get_regex()}{self.__value_parser.get_regex(with_value_capture)}"


# ^([a-zA-Z_][\w]*)="([\s\S]*[^\\])"[\t ]*$|^([a-zA-Z_][\w]*)='([\s\S]*[^\\])'[\t ]*$|^([a-zA-Z_][\w]*)=([^"\t ].*)$
# ^([a-zA-Z_][\w]*)="([\s\S]*?[^\\])"|^([a-zA-Z_][\w]*)='([\s\S]*?[^\\])'|^([a-zA-Z_][\w]*)=([^"\t ].*)$
# ^([a-zA-Z_][\w]*)="((?:[^"]*(?:\\|\\")*)*)"[\t ]*$
# str.replace(r"\\", "")
# str.replace(r"\\"", "")
# str.replace(r"\\r", "")
# str.replace(r"\\r\n", "")
# str.replace(r"\\n\r", "")
# str.replace(r"\\n", "")

# https://regex101.com/r/Dr9Dyt/1
# Проблема https://regex101.com/r/rdVI51/1
# https://regex101.com/r/YMUFSJ/1
# https://regex101.com/r/3PLIai/1
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
        else if self.__is_bool(raw_string_value):
            return

    def __is_bool(self, raw_string_value):
        return self.__bool_from_string.is_bool(raw_string_value)

    def __is_integer(self, raw_string_value):
        return raw_string_value.trim().isdigit()


# https://habr.com/ru/articles/658463/
class TransmissionDaemon:
    def __init__(self):
        print("")


def help_usage():
    print(
        "config <config-parameter-name>\n"
        "  or\n"
        "run <none parameters>\n"
        "  or\n"
        "check <none parameters>\n"
        "  or\n"
        "user_ovpn <user name>\n"
        "  or\n"
        "vm_create <vm name> <image size in gibibytes>\n"
        "  or\n"
        "vm_install <vm name> <path to iso disk with os distributive>\n"
        "  or\n"
        "vm_run <vm name>\n"
        "\n"
        "\n"
        "  config - get config parameter value by name from open-vpn.config.json\n"
        "    available <config-parameter-name> see in open-vpn.config.json\n"
        "\n"
        "  run - run OpenVpn server\n"
        "\n"
        "  check - check you NAT type for udp hole punching\n"
        "\n"
        "  user_ovpn - generate openvpn client config file (*.ovpn) for specified user\n"
        "\n"
        "  vm_create - create vm image with <vm name> and <image size in gibibytes>,\n"
        "    default image size 20 GiB\n"
        "\n"
        "  vm_install - install os on vm image created by vm_create command\n"
        "\n"
        "  vm_run - run vn by name, see vm_create and vm_install commands\n"
    )


def main():
    if len(sys.argv) == 1:
        help_usage()
        return

    command = sys.argv[1]
    if command == "config":
        if len(sys.argv) == 3:
            config_parameter_name = str(sys.argv[2])
            print(OpenVpnConfig().get_config_parameter_strong(config_parameter_name))
            return
        else:
            help_usage()
            return

    elif command == "run":
        Daemon().run()

    elif command == "check":
        open_vpn_config = OpenVpnConfig()
        MyExternalIpAddressAndPort(open_vpn_config.get_server_port()).get()

    elif command == "user_ovpn":
        if len(sys.argv) == 3:
            user_name = str(sys.argv[2])
            open_vpn_config = OpenVpnConfig()
            my_ip_address_and_port = IpAddressAndPort(
                TextConfigReader(open_vpn_config.get_my_current_ip_address_and_port()).get())
            print(OpenVpnClientConfigGenerator(my_ip_address_and_port, user_name).generate())
            return
        else:
            help_usage()
            return

    elif command == "vm_create":
        if len(sys.argv) >= 3:
            config = OpenVpnConfig()

            name = str(sys.argv[2])

            image_size_in_gib = 20
            if len(sys.argv) >= 4:
                image_size_in_gib_as_string = sys.argv[3]
                if image_size_in_gib_as_string is not None:
                    image_size_in_gib = int(image_size_in_gib_as_string)

            print(VmRegistry(config.get_vm_registry_path()).create(name, image_size_in_gib).get_image_path())
            return
        else:
            help_usage()
            return

    elif command == "vm_install":
        if len(sys.argv) >= 3:
            vm_name = str(sys.argv[2])
            path_to_os_iso_disk = Path(sys.argv[3])
            if not path_to_os_iso_disk.exists():
                raise Exception("VM installer \"{}\" NOT FOUND".format(path_to_os_iso_disk))

            config = OpenVpnConfig()

            local_network_interface = OpenVpnConfig.get_or_default_local_network_interface(
                config.get_local_network_interface())

            network_bridge = NetworkBridge(config.get_server_name(), config.get_vm_bridge_ip_address_and_mask(),
                                           config.get_dns_config_dir(), local_network_interface)

            vm_registry = VmRegistry(config.get_vm_registry_path())
            vm_meta_data = vm_registry.get_with_verifying(vm_name)
            virtio = Virtio(config)
            vm = VirtualMachine(network_bridge, vm_meta_data, path_to_os_iso_disk, virtio=virtio)
            vm.run()
            return
        else:
            help_usage()
            return

    elif command == "vm_run":
        if len(sys.argv) >= 2:
            vm_name = str(sys.argv[2])

            config = OpenVpnConfig()
            network_bridge = NetworkBridge(config.get_server_name(), config.get_vm_bridge_ip_address_and_mask(),
                                           config.get_dns_config_dir(), config.get_internet_network_interface())

            vm_registry = VmRegistry(config.get_vm_registry_path())
            vm_meta_data = vm_registry.get_with_verifying(vm_name)

            local_network_interface = OpenVpnConfig.get_or_default_local_network_interface(
                config.get_local_network_interface())

            vm_ssh_forwarding = VmSshForwarding(vm_meta_data, local_network_interface,
                                                vm_meta_data.get_ssh_forward_port())
            vm_rdp_forwarding = VmRdpForwarding(vm_meta_data, local_network_interface,
                                                vm_meta_data.get_rdp_forward_port())
            tcp_forwarding_thread = threading.Thread(target=lambda: (vm_ssh_forwarding.add_with_retry(),
                                                                     vm_rdp_forwarding.add_with_retry()))
            tcp_forwarding_thread.start()

            vm = VirtualMachine(network_bridge, vm_meta_data)
            vm.run()
            tcp_forwarding_thread.join()
            return
        else:
            help_usage()
            return

    elif command == "vm_ssh_fwd":
        if len(sys.argv) >= 2:
            vm_name = str(sys.argv[2])
            project_config = OpenVpnConfig()
            vm_registry = VmRegistry(project_config.get_vm_registry_path())
            vm_metadata = vm_registry.get_with_verifying(vm_name)

            ssh_input_port_from_user = input(
                "Enter vm \"{}\" SSH port [{}-{}]: ".format(vm_metadata.get_name(), TcpPort.TCP_PORT_MIN,
                                                            TcpPort.TCP_PORT_MAX))
            if not TcpPort.is_valid(ssh_input_port_from_user):
                print("INVALID!!! reexecute command")

            vm_registry.set_ssh_forward_port(vm_name, ssh_input_port_from_user)
        else:
            help_usage()
            return

    elif command == "vm_rdp_fwd":
        if len(sys.argv) >= 2:
            vm_name = str(sys.argv[2])
            project_config = OpenVpnConfig()
            vm_registry = VmRegistry(project_config.get_vm_registry_path())
            vm_metadata = vm_registry.get_with_verifying(vm_name)

            ssh_input_port_from_user = input(
                "Enter vm \"{}\" SSH port [{}-{}]: ".format(vm_metadata.get_name(), TcpPort.TCP_PORT_MIN,
                                                            TcpPort.TCP_PORT_MAX))
            if not TcpPort.is_valid(ssh_input_port_from_user):
                print("INVALID!!! reexecute command")

            vm_registry.set_rdp_forward_port(vm_name, ssh_input_port_from_user)
        else:
            help_usage()
            return

    elif command == "test":
        print("XXX")
        print(NetworkInterface("lo").get_ipv4_interface_if())
        print(NetworkInterface("lo").get_ipv6_interface_if())
        print(NetworkInterface.get_internet_if())
        # return
        # print(ResolvConf().get_nameserver_list())
        # ResolvConf().add_nameserver_if("172.20.0.1")
        # print(ResolvConf().get_nameserver_list())
        # ResolvConf().remove_nameserver("172.20.0.1")
        # print(ResolvConf().get_nameserver_list())
        # return
        config = OpenVpnConfig()
        vm_bridge_name = config.get_server_name()
        print("vm_bridge_name = {}".format(vm_bridge_name))
        # print("ttt: {}".format(list(vm_bridge_ip_network.hosts())))
        # return
        network_bridge = NetworkBridge(vm_bridge_name, config.get_vm_bridge_ip_address_and_mask(),
                                       config.get_dns_config_dir(), config.get_or_default_internet_network_interface())
        # network_bridge.create()
        # time.sleep(30)
        # print("network_bridge.close()")
        # network_bridge.close()
        # print("network_bridge.close() +++")
        # time.sleep(30)
        vm = VirtualMachine(network_bridge)
        vm.run()


if __name__ == '__main__':
    main()
