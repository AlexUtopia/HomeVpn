import atexit
import os.path
import re
import subprocess
import json
import ipaddress
import time
import sys
import urllib.request
import urllib.parse
import stun
import getpass
import tuntap
import iptc
import socket
import platform


# https://tproger.ru/translations/demystifying-decorators-in-python/


class RealPath:
    def __init__(self, file_name_or_relative_file_path):
        self.__file_name_or_relative_file_path = str(file_name_or_relative_file_path)

    def get(self):
        this_script_dir = os.path.dirname(os.path.realpath(__file__))
        result = os.path.abspath(os.path.join(this_script_dir, self.__file_name_or_relative_file_path))
        return result

    def __str__(self):
        return self.get()

    def __repr__(self):
        return self.__str__()


class TextConfigReader:
    def __init__(self, config_file_path, encoding="utf-8"):
        self.__config_file_path = str(config_file_path)
        self.__encoding = str(encoding)

    def get(self):
        return self.__load_from_config()

    def __load_from_config(self):
        result = ""
        with open(self.__config_file_path, mode="rt", encoding=self.__encoding) as config_file:
            result += str(config_file.read())
        # print("Load from config: {}".format(result))
        return result


class TextConfigWriter:
    def __init__(self, config_file_path, encoding="utf-8"):
        self.__config_file_path = str(config_file_path)
        self.__encoding = str(encoding)

    def set(self, data):
        with open(self.__config_file_path, mode="wt", encoding=self.__encoding) as config_file:
            config_file.write(str(data))
        return self.__config_file_path


class JsonConfigLoader:
    def __init__(self, config_file_path, encoding="utf-8"):
        self.__text_config_reader = TextConfigReader(config_file_path, encoding)

    def get(self):
        return json.loads(self.__text_config_reader.get())


class StunServerAddressList(JsonConfigLoader):
    def __init__(self, config_file_path=RealPath("stun-servers.config.json")):
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
        result = urllib.parse.urlparse(self.__stun_server_address, False)
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


class TelegramBotConfig(JsonConfigLoader):
    def __init__(self, config_file_path=RealPath("telegram-bot.config.json")):
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
    def __init__(self, open_vpn_config_path=RealPath("open-vpn.config.json")):
        self.__config_reader = JsonConfigLoader(open_vpn_config_path)

    def get_server_name(self):
        return self.get_config_parameter("open_vpn_server_name")

    def get_server_port(self):
        return int(self.get_config_parameter("open_vpn_server_port"))

    def get_keys_dir(self):
        return self.get_config_parameter("open_vpn_keys_dir")

    def get_server_logs_dir(self):
        return self.get_config_parameter("open_vpn_server_logs_dir")

    def get_client_keys_dir(self):
        return self.get_config_parameter("open_vpn_client_keys_dir")

    def get_client_logs_dir(self):
        return self.get_config_parameter("open_vpn_client_logs_dir")

    def get_easy_rsa_version(self):
        return self.get_config_parameter("easy_rsa_version")

    def get_watchdog_user_name(self):
        return self.get_config_parameter("watchdog_user_name")

    def get_my_current_ip_address_and_port(self):
        return self.get_config_parameter("my_current_ip_address_and_port")

    def get_vm_bridge_ip_network(self):
        return ipaddress.ip_network(self.get_config_parameter("vm_bridge_ip_network"))

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

    def get_config_parameter(self, name):
        return str(self.__config_reader.get()[name])

    @staticmethod
    def _parse(config_as_string, begin_label, end_label):
        regex = re.compile(r"({}[\s\S]*{})".format(begin_label, end_label), re.MULTILINE)
        return regex.findall(config_as_string)[0]


class OpenVpnClientConfig(OpenVpnConfig):
    def __init__(self, user_name, open_vpn_config_path=RealPath("open-vpn.config.json")):
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
    def __init__(self, config_template_file_path=RealPath("open-vpn-server.config.template"),
                 output_config_dir=RealPath(".")):
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


class OpenVpnClientConfigGenerator:
    def __init__(self, ip_address_and_port, user_name,
                 config_template_file_path=RealPath("open-vpn-client.config.template"),
                 output_client_config_dir=RealPath(".")):
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
        self.__key_value_config.add("port", self.__ip_address_and_port.get_port())

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
    def __init__(self, name):
        self.__name = str(name)

    def __str__(self):
        return self.__name

    def __repr__(self):
        return self.__str__()

    @staticmethod
    def list():
        return socket.if_nameindex()

    @staticmethod
    def get_internet_if():
        # fixme utopia Костыль
        return NetworkInterface("wlp9s0")

    def exists(self):
        for not_used, if_name in self.list():
            if if_name == self.__name:
                return True
        return False

    def is_wireless(self):
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


class BridgeFirewall:
    """
    # @details см. https://wiki.gentoo.org/wiki/QEMU/Bridge_with_Wifi_Routing и https://wiki.gentoo.org/wiki/QEMU/Options#Virtual_network_cable_.28TAP.29
    """

    def __init__(self, bridge, internet_if):
        self.__bridge_name = str(bridge)
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


class NetworkBridge:
    def __init__(self, name, ip_network):  # fixme utopia Взять названме с конфига (<open_vpn_server_name>-brigde)
        self.__interface = NetworkInterface(name)
        self.__ip_interface = ipaddress.ip_interface(str(ip_network))
        self.__bridge_ip_address = self.__ip_interface.ip + 1
        self.__bridge_prefixlen = self.__ip_interface.network.prefixlen
        atexit.register(self.close)

    def create(self):
        if self.__interface.exists():
            return

        self.__set_ip_forwarding()

        try:
            subprocess.check_call("ip link add {} type bridge".format(self.__interface), shell=True)
            subprocess.check_call(
                "ip addr add {} dev {}".format(self.__get_bridge_ip_and_mask(), self.__interface),
                shell=True)
            subprocess.check_call("ip link set {} up".format(self.__interface), shell=True)
        except:
            self.close()

        self.__setup_firewall()
        self.__setup_bridge_dhcp()

    def close(self):
        if not self.__interface.exists():
            return

        self.__clear_firewall()

        subprocess.check_call("ip link set {} down".format(self.__interface), shell=True)
        subprocess.check_call("ip link delete {} type bridge".format(self.__interface), shell=True)

    def add_and_configure_tap(self, tap_if):
        # tap_if.config(self.__ip_interface.network)
        subprocess.check_call("ip link set {} master {}".format(tap_if, self.__interface), shell=True)

    @staticmethod
    def __set_ip_forwarding():
        subprocess.check_call("sysctl -w net.ipv4.ip_forward=1", shell=True)

    def __setup_firewall(self):
        internet_if = NetworkInterface.get_internet_if()
        BridgeFirewall(self.__interface, internet_if).setup()

    def __clear_firewall(self):
        internet_if = NetworkInterface.get_internet_if()
        BridgeFirewall(self.__interface, internet_if).clear_at_exit()

    def __get_bridge_ip_and_mask(self):
        return "{}/{}".format(self.__bridge_ip_address, self.__bridge_prefixlen)

    def __setup_bridge_dhcp(self):
        # fixme utopia --dhcp-range прибито гвоздями
        subprocess.check_call(
            "dnsmasq --interface={} --bind-interfaces --dhcp-range=172.20.0.2,172.20.255.254".format(self.__interface),
            shell=True)


class TapName:
    NAME_TEMPLATE = "homevpn-tap"  # fixme utopia Взять названме с конфига (open_vpn_server_name)
    REGEX_PATTERN = r"^{}([0-9]+)".format(NAME_TEMPLATE)
    INDEX_NOT_FOUND = 1  # fixme utopia Индекс как-то криво вяжется с назначением ip адесов внутри бриджа

    def __init__(self):
        self.__index = TapName.INDEX_NOT_FOUND
        for not_used, if_name in NetworkInterface.list():
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

    def config(self, ip_network):
        if not self.__interface.exists():
            return

        subprocess.check_call(
            "ip addr add {} dev {}".format(self.__get_bridge_ip_and_mask(ip_network), self.__interface),
            shell=True)

    def close(self):
        if not self.__interface.exists():
            return

        subprocess.check_call("ip link set {} down".format(self.__interface), shell=True)
        subprocess.check_call("ip tuntap del dev {} mode tap".format(self.__interface), shell=True)

    def __get_bridge_ip_and_mask(self, ip_network):
        increment_ip = self.__tap_name.get_index()
        if increment_ip >= ip_network.num_addresses:
            raise Exception("AHTUNG!!!")  # fixme utopia Текстовка

        return "{}/{}".format(ip_network.network_address + increment_ip, ip_network.prefixlen)


class VirtualMachine:
    def __init__(self, network_bridge):
        self.__tap = Tap()
        self.__network_bridge = network_bridge

    def run(self):
        self.__network_bridge.create()

        command_line = self.__command_line()
        print(command_line)
        subprocess.check_call(command_line, shell=True)

    def __command_line(self):
        command_parts_list = [self.__qemu_command_line(), self.__kvm_enable(), self.__ram_size(), self.__network(),
                              self.__other(), self.__disk()]
        return " ".join(command_parts_list)

    def __qemu_command_line(self):
        return "qemu-system-{}".format(platform.machine())

    def __kvm_enable(self):
        return "-enable-kvm"

    def __ram_size(self):  # fixme utopia Использовать psutil
        return "-m 4096"

    def __network(self):
        self.__tap.create()
        self.__network_bridge.add_and_configure_tap(self.__tap)

        tap_name = str(self.__tap)
        netdev_id = "{}-id".format(tap_name)

        return "-netdev tap,ifname={0},script=no,downscript=no,id={1} -device virtio-net,netdev={1},mac=00:12:35:56:78:9a".format(
            tap_name, netdev_id)

    def __disk(self):
        return "disk1.img"

    def __other(self):
        # -cdrom ~/Загрузки/linuxmint-20.2-cinnamon-64bit.iso
        return "-vga std -vnc 127.0.0.1:2"


class Daemon:
    SLEEP_BEFORE_RECONNECT_SEC = 30
    SLEEP_AFTER_SERVER_START_SEC = 5

    def __init__(self):
        self.__open_vpn_config = OpenVpnConfig()

    def run(self):
        open_vpn_server_port = self.__open_vpn_config.get_server_port()

        while True:
            my_ip_address_and_port = MyExternalIpAddressAndPort(open_vpn_server_port).get()

            TextConfigWriter(self.__open_vpn_config.get_my_current_ip_address_and_port()).set(my_ip_address_and_port)

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


def help_usage():
    print(
        "config <config-parameter-name>\n"
        "  or\n"
        "run <none parameters>\n"
        "  or\n"
        "check <none parameters>\n"
        "  or\n"
        "user_ovpn <user name>\n"
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
        "")


def main():
    if len(sys.argv) == 1:
        help_usage()
        return

    command = sys.argv[1]
    if command == "config":
        if len(sys.argv) == 3:
            config_parameter_name = str(sys.argv[2])
            print(OpenVpnConfig().get_config_parameter(config_parameter_name))
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

    elif command == "test":
        vm_bridge_name = OpenVpnConfig().get_server_name()
        vm_bridge_ip_network = OpenVpnConfig().get_vm_bridge_ip_network()
        print("vm_bridge_name = {} | vm_bridge_ip_network = {}".format(vm_bridge_name, vm_bridge_ip_network))

        network_bridge = NetworkBridge(vm_bridge_name, vm_bridge_ip_network)
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
