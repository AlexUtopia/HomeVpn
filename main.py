import re
import subprocess
import json
import ipaddress
import urllib.request


class StunServerAddressList:
    def __init__(self, config_file_path=None):
        if config_file_path is None:
            self.__config_file_path = "./stun-servers.config.json"
        else:
            self.__config_file_path = str(config_file_path)

    def get(self):
        return self.__load_from_config()

    def __load_from_config(self):
        config_file = open(self.__config_file_path)
        result = json.load(config_file)
        config_file.close()
        print("Load STUN servers from config: {}".format(result))
        return result


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

    def __init__(self, local_port, config_file_path=None):
        self.__local_port = local_port
        if config_file_path is None:
            self.__config_file_path = "./openvpn-server.config"
        else:
            self.__config_file_path = str(config_file_path)

    def run(self):
        result = subprocess.run(
            [self.OPEN_VPN, "--config", self.__config_file_path, "--port", str(self.__local_port), "--daemon"],
            capture_output=True,
            text=True, check=True
        )
        print("OpenVpn server STARTED!!!")


class TelegramClient:


# curl -X POST -H 'Content-Type: application/json' -d '{"chat_id": "-687389280", "text": "Galina hello!!! this message from me for you (from my linux console, hhhhhh)))))"}' https://api.telegram.org/bot5296572881:AAFkHMbDlDvpWR2mEC3p2q0sb8ycOxbQmnI/sendMessage



stun_client22 = MyExternalIpAddressAndPort(35000)
stun_client22.get()
