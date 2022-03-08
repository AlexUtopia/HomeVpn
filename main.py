import re
import subprocess
import json
import ipaddress
import time
import sys
import urllib.request
import urllib.parse


# https://tproger.ru/translations/demystifying-decorators-in-python/

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
            config_file.write(data)
        return self.__config_file_path


class JsonConfigLoader:
    def __init__(self, config_file_path, encoding="utf-8"):
        self.__text_config_reader = TextConfigReader(config_file_path, encoding)

    def get(self):
        return json.loads(self.__text_config_reader.get())


class StunServerAddressList(JsonConfigLoader):
    def __init__(self, config_file_path=None):
        if config_file_path is None:
            super().__init__("./stun-servers.config.json")
        else:
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
    REGEX_PATTERN = r"MappedAddress.*=.*{}".format(IpAddressAndPort.REGEX_PATTERN)
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
        print("Stun client return: {}".format(result))

        if result.returncode != self.STUN_RESPONSE_OK:
            raise Exception("Stun client call FAIL: {}".format(result.stderr))

        return result.stderr

    def __parse_stun_client_output(self, stun_client_output):
        regex = re.compile(self.REGEX_PATTERN)
        result_raw = regex.findall(stun_client_output)

        result = []
        for it in result_raw:
            result.append(IpAddressAndPort(it))

        print("Stun client parsed output: {}".format(result))
        return result


class MyExternalIpAddressAndPort:
    def __init__(self, local_port):
        self.__local_port = local_port

    def get(self):
        stun_server_address_list = StunServerAddressList()
        for stun_server_address in stun_server_address_list.get():
            try:
                stun_client = StunClient(stun_server_address, self.__local_port)
                result = stun_client.get_my_ip_address_and_port()
                print("My external IP address and port: {}".format(result))
                return result
            except Exception:
                print("[WARNING]")
        raise Exception("My external IP address and port NOT FOUND")


class OpenVpnServer:
    OPEN_VPN = "openvpn"

    def __init__(self, local_port, config_file_path="./openvpn-server.config"):
        self.__local_port = local_port
        self.__config_file_path = str(config_file_path)

    def run(self):
        result = subprocess.run(
            [self.OPEN_VPN, "--config", self.__config_file_path, "--port", str(self.__local_port), "--daemon"],
            capture_output=True,
            text=True
        )
        print("OpenVpn server return: {}".format(result))

        if result.returncode:
            raise Exception("OpenVpn server start FAIL: {}".format(result.stderr))

        print("OpenVpn server start OK")


class OpenVpnClient:
    OPEN_VPN = "openvpn"

    def __init__(self, local_port, config_file_path):
        self.__local_port = local_port
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
    def __init__(self, config_file_path="./telegram-bot.config.json"):
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
    def __init__(self, open_vpn_config_path="./open-vpn.config.json"):
        self.__config_reader = JsonConfigLoader(str(open_vpn_config_path))

    def get_server_name(self):
        return self.get_config_parameter("open_vpn_server_name")

    def get_server_port(self):
        return int(self.get_config_parameter("open_vpn_server_port"))

    def get_keys_dir(self):
        return self.get_config_parameter("open_vpn_keys_dir")

    def get_client_keys_dir(self):
        return self.get_config_parameter("open_vpn_client_keys_dir")

    def get_easy_rsa_version(self):
        return self.get_config_parameter("easy_rsa_version")

    def get_watchdog_user_name(self):
        return self.get_config_parameter("watchdog_user_name")

    def get_ca_cert_path(self):
        return "{}/ca.crt".format(self.get_keys_dir())

    def get_tls_auth_key_path(self):
        return "{}/ta.key".format(self.get_keys_dir())

    def get_ca_cert(self):
        return self.__parse(TextConfigReader(self.get_ca_cert_path()).get(), "-----BEGIN CERTIFICATE-----",
                            "-----END CERTIFICATE-----")

    def get_tls_auth_key(self):
        return self.__parse(TextConfigReader(self.get_tls_auth_key_path()).get(),
                            "-----BEGIN OpenVPN Static key V1-----",
                            "-----END OpenVPN Static key V1-----")

    def get_config_parameter(self, name):
        return str(self.__config_reader.get()[name])

    def __parse(self, config_as_string, begin_label, end_label):
        regex = re.compile(r"({}[\s\S]*{})".format(begin_label, end_label), re.MULTILINE)
        if not regex.match():
            print("[W] config_as_string: {}".format(config_as_string))
            return ""  # fixme utopia бросить исключение

        return regex.findall(config_as_string)[0]


class OpenVpnClientConfig(OpenVpnConfig):
    def __init__(self, user_name, open_vpn_config_path="./open-vpn.config.json"):
        super().__init__(open_vpn_config_path)
        self.__user_name = user_name

    pass

    def get_client_cert_path(self):
        return "{}/{}.crt".format(self.get_client_keys_dir(), self.__user_name)

    def get_client_key_path(self):
        return "{}/{}.key".format(self.get_client_keys_dir(), self.__user_name)

    def get_client_cert(self):
        return self.__parse(TextConfigReader(self.get_client_cert_path()).get(), "-----BEGIN CERTIFICATE-----",
                            "-----END CERTIFICATE-----")

    def get_client_key(self):
        return self.__parse(TextConfigReader(self.get_client_key_path()).get(), "-----BEGIN PRIVATE KEY-----",
                            "-----END PRIVATE KEY-----")

    # fixme utopia Получить весь список пользователей
    # fixme utopia Сохранять вместе с логином пользователя telegram


class OpenVpnConfigKeyValue:
    def __init__(self):
        self.__container = {}

    def add(self, key, value):
        as_xml = False
        self.__add(key, value, as_xml)

    def add_as_xml(self, key, value):
        as_xml = True
        self.__add(key, value, as_xml)

    def render(self):
        result = ""
        for key, value in self.__container.items():
            result += self.__render_key_value(key, value)
        return result

    def __add(self, key, value, as_xml):
        if value is None:
            self.__container[str(key)] = {"value": None, "as_xml": as_xml}
        else:
            self.__container[str(key)] = {"value": str(value), "as_xml": as_xml}

    def __render_key_value(self, key, value):
        if bool(value.is_xml):
            if value.value is None:
                result = "<{0}></{0}>\n".format(key)
            else:
                result = "<{0}>\n{1}\n</{0}>\n".format(key, value)
        else:
            if value.value is None:
                result = "{}\n".format(key)
            else:
                result = "{} {}\n".format(key, value)
        return result


class OpenVpnClientConfigGenerator:
    def __init__(self, ip_address_and_port, user_name,
                 client_config_template_file_path="./open-vpn-client.config.template", output_client_config_dir="."):
        self.__client_config_template_reader = TextConfigReader(client_config_template_file_path)
        self.__key_value_config = OpenVpnConfigKeyValue()
        self.__open_vpn_client_config = OpenVpnClientConfig(user_name)
        self.__output_client_config_file = TextConfigWriter(
            "{}/{}.ovpn".format(str(output_client_config_dir), user_name))
        self.__ip_address_and_port = ip_address_and_port

    def generate(self):
        return self.__output_client_config_file.set(self.__render_to_string())

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

    def __parse_template(self):
        regex = re.compile(r"^[ \t]*([a-z\-_0-9]+)[ \t]*(.*)\n", re.MULTILINE)
        tmp = regex.findall(self.__client_config_template_reader.get())

        if len(tmp) == 0:
            raise Exception("Parse ip_address_and_port FAIL")  # fixme utopia text

        for t in tmp:
            self.__key_value_config.add(t[0], t[1])

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


class Main:
    SLEEP_BEFORE_RECONNECT_SEC = 30

    def __init__(self):
        self.__open_vpn_config = OpenVpnConfig()

    def run(self):
        self.__init()

        open_vpn_server_port = self.__open_vpn_config.get_server_port()

        while True:
            my_ip_address_and_port = MyExternalIpAddressAndPort(open_vpn_server_port).get()

            TelegramClient().send_message(
                "Хорошего дня, лови новые параметры подключения\nIP Address: {}\nPort: {}".format(
                    my_ip_address_and_port.get_ip_address(), my_ip_address_and_port.get_port()))

            watchdog_user_config_path = OpenVpnClientConfigGenerator(my_ip_address_and_port, self.__open_vpn_config.get_watchdog_user_name()).generate()

            # fixme utopia Сгенерировать новые ovpn для всех клиентов и разослать их всем клиентам telegram бота
            #              список чатов видимо придётся копить в каком-то локальном конфиге, т.к. у телеграма нет такого метода в api

            try:  # fixme utopia Перепроверить что мы можем засечь разрыв соединения, к примеру, выключить WiFi
                OpenVpnClient(watchdog_user_config_path).run()
            except Exception:
                print("Try udp hole punching and RECONNECT")

            time.sleep(self.SLEEP_BEFORE_RECONNECT_SEC)

    def __init(self):
        # fixme utopia Конфигурацию сервера нужно генерировать из шаблона и подсовывать серверу ovpn файл
        OpenVpnServer(self.__open_vpn_config.get_server_port()).run()


# fixme utopia Выставить main для получения данных с open-vpn.config.json
#              Скрипты build-client.sh и setup-easy-rsa.sh должны использовать open-vpn.config.json

# fixme utopia Telegram бот в отдельный поток для обслуживания пользователей, работаем в режиме long polling
#              my_ip_address_and_port сделать шареной между потоками переменной

# fixme utopia Провериь динамическое добавление клиента на работающем OpenVpn сервере (сервер не перезапускать)


def help_usage():
    print(
        "config <config-parameter-name>\n"
        "  or\n"
        "run <none parameters>\n"
        "  or\n"
        "check <none parameters>\n"
        "\n"
        "\n"
        "  config - get config parameter value by name from open-vpn.config.json\n"
        "    available <config-parameter-name> see in open-vpn.config.json\n"
        "\n"
        "  run - run OpenVpn server\n"
        "\n"
        "  check - check you NAT type for udp hole punching\n"
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
        Main().run()


if __name__ == '__main__':
    main()
