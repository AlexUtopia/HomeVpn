from __future__ import annotations

import ipaddress
import psutil
import re
import socket
import subprocess


class NetworkInterface:
    # https://developers.google.com/speed/public-dns/docs/using#addresses
    GOOGLE_PUBLIC_DNS_IPV4_1 = ipaddress.ip_address("8.8.8.8")
    GOOGLE_PUBLIC_DNS_IPV4_2 = ipaddress.ip_address("8.8.4.4")

    GOOGLE_PUBLIC_DNS_IPV6_1 = ipaddress.ip_address("2001:4860:4860:0:0:0:0:8888")
    GOOGLE_PUBLIC_DNS_IPV6_2 = ipaddress.ip_address("2001:4860:4860:0:0:0:0:8844")

    NAME_LENGTH_MIN = 1
    NAME_LENGTH_MAX = 16

    def __init__(self, name: str):
        self.__name = name

    def __str__(self):
        return self.__name

    def __repr__(self):
        return self.__str__()

    @staticmethod
    def list() -> list[str]:
        return list(psutil.net_if_addrs().keys())

    @staticmethod
    def get_internet_if_strong() -> NetworkInterface:
        result = NetworkInterface.get_internet_if()
        if not result:
            raise Exception("Internet interface NOT FOUND")
        return result

    @staticmethod
    def get_internet_if() -> NetworkInterface | None:
        # https://unix.stackexchange.com/questions/473803/how-to-find-out-the-interface-which-is-being-used-for-internet

        cmd_result = subprocess.run(f"ip route get {NetworkInterface.GOOGLE_PUBLIC_DNS_IPV4_1}", shell=True,
                                    capture_output=True, text=True)
        if cmd_result.returncode:
            raise Exception(f"Get internet network interface FAIL: {cmd_result}")

        regex = re.compile(fr".* dev (\S{{{NetworkInterface.NAME_LENGTH_MIN},{NetworkInterface.NAME_LENGTH_MAX}}}) .*",
                           re.MULTILINE)
        tmp = regex.findall(cmd_result.stdout)
        if len(tmp) == 0:
            return None

        result = NetworkInterface(tmp[0])
        if not result.exists():
            return None

        return result

    def exists(self) -> bool:
        return self.__name in NetworkInterface.list()

    def is_wireless(self) -> bool:
        # https://www.linux.org.ru/forum/general/11160638
        # fixme utopia Реализовать
        return True

    def is_internet(self) -> bool:
        return True

    def is_wired(self) -> bool:
        # fixme utopia Реализовать
        return True

    def is_bridged(self) -> bool:
        # fixme utopia Реализовать
        return True

    def get_ipv4_interface_if(self) -> ipaddress.IPv4Interface | None:
        for net_if_name, snicaddr_list in psutil.net_if_addrs().items():
            if net_if_name == self.__name:
                for family, address, netmask, broadcast, ptp in snicaddr_list:
                    if family == socket.AddressFamily.AF_INET:
                        return ipaddress.ip_interface(f"{address}/{netmask}")
        return None

    def get_ipv6_interface_if(self)-> ipaddress.IPv6Interface | None:
        for net_if_name, snicaddr_list in psutil.net_if_addrs().items():
            if net_if_name == self.__name:
                for family, address, netmask, broadcast, ptp in snicaddr_list:
                    if family == socket.AddressFamily.AF_INET6:
                        return ipaddress.ip_interface(address)
        return None
