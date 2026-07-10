from __future__ import annotations

import ipaddress
import netaddr
import os
import pathlib
import randmac
import socket
import typing

from lib.python.network import TcpPort
from lib.python.system import Arch
from lib.python.vm import QemuPlatform, VmName


# https://stackoverflow.com/questions/17493307/creating-set-of-objects-of-user-defined-class-in-python
class VmMetaData:
    class Parameter[T]:
        def __init__(self, name: str,
                     parameter_dir_path: str | os.PathLike[str],
                     value_default_handler: typing.Callable[[], T] | None = None,
                     deserialize_handler: typing.Callable[[str], T] = lambda x: type[T](x),
                     serialize_handler: typing.Callable[[T], str] = lambda x: str(x),
                     encoding="utf-8",
                     extension=".txt"):
            self.path = pathlib.Path(parameter_dir_path).resolve() / f"{name}{extension}"
            self.__value_default_handler = value_default_handler
            self.__deserialize_handler = deserialize_handler
            self.__serialize_handler = serialize_handler
            self.__encoding = encoding

        def __str__(self):
            return str(self.load())

        def __repr__(self):
            return self.__str__()

        def exists(self) -> bool:
            return self.path.exists() and self.path.resolve().is_file()

        def raise_exception_if_non_exists(self) -> None:
            if not self.exists():
                raise Exception(f'[Vm] Parameter "{self.path.name}" in "{self}" NOT FOUND')

        def load(self) -> T | None:
            result = self.__value_default_handler() if self.__value_default_handler else None
            if self.exists():
                result = self.path.read_text(encoding=self.__encoding)
                if self.__deserialize_handler:
                    result = self.__deserialize_handler(result)
            elif result:
                self.store(result)

            return result

        def store(self, value: T | str) -> None:
            self.makedirs()
            if isinstance(value, str):
                value_serialized = value
            elif self.__serialize_handler:
                value_serialized = self.__serialize_handler(value)
            else:
                value_serialized = str(value)
            self.path.write_text(value_serialized, encoding=self.__encoding)

        def makedirs(self) -> None:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    IMAGE_EXTENSION = ".img"

    ARCH_DEFAULT = "x86_64"

    def __init__(self, name: VmName | str,
                 image_dir_path: str | os.PathLike[str],
                 platform: QemuPlatform = QemuPlatform(arch=Arch(ARCH_DEFAULT)),
                 vnc_display_port: TcpPort = TcpPort.get_vnc_port(10)):
        self.__image_path = VmMetaData.Parameter[VmName](str(VmName(name)), image_dir_path,
                                                         extension=self.IMAGE_EXTENSION)
        self.__mac_address = VmMetaData.Parameter[netaddr.EUI]("mac_address", image_dir_path,
                                                               value_default_handler=lambda: netaddr.EUI(
                                                                   str(randmac.RandMac())))
        self.__ssh_forward_port = VmMetaData.Parameter[TcpPort]("ssh_forward_port", image_dir_path)
        self.__rdp_forward_port = VmMetaData.Parameter[TcpPort]("rdp_forward_port", image_dir_path)
        self.__dns_suffix = dns_suffix
        self.__platform = VmMetaData.Parameter[QemuPlatform]("platform", image_dir_path,
                                                             value_default_handler=lambda: platform)
        self.__vnc_display_port = VmMetaData.Parameter[TcpPort]("vnc_display_port", image_dir_path,
                                                                value_default_handler=lambda: vnc_display_port)
        self.makedirs()

    def __str__(self):
        return str(self.__dict__)

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

    def check_image_exists(self) -> None:
        self.__image_path.raise_exception_if_non_exists()

    def get_name(self) -> str:
        return self.__image_path.path.stem

    def get_image_path(self) -> pathlib.Path:
        return self.__image_path.path

    def image_exists(self) -> bool:
        return self.__image_path.exists()

    def get_mac_address(self) -> netaddr.EUI:
        result = self.get_mac_address_path().load()
        if not result:
            raise Exception("[Vm] MAC address UNDEFINED")
        return result

    def get_mac_address_path(self) -> VmMetaData.Parameter[netaddr.EUI]:
        return self.__mac_address

    def get_mac_address_as_string(self) -> str:
        result = self.get_mac_address()
        result.dialect = netaddr.mac_unix_expanded
        return str(result)

    def get_hostname(self) -> str:
        return DnsDhcpProvider.get_hostname(self.get_name(), self.__dns_suffix)

    ## Получить IP адрес запущенной виртуальной машины
    # @warning IP адрес виртуальной машине раздаётся через DHCP, поэтому до запуска виртуальной машины получить её IP адрес нельзя
    # @return IP адрес запущенной виртуальной машины или исключение, если не удалось получить результат
    def get_ip_address_strong(self) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
        vm_hostname = self.get_hostname()
        for _family, _type, _proto, _canonname, sockaddr in socket.getaddrinfo(vm_hostname, TcpPort.DNS_PORT_DEFAULT):
            return ipaddress.ip_address(sockaddr[0])
        raise Exception(f'[VmMetaData] Resolve vm hostname "{vm_hostname}" FAIL')

    def get_ip_address(self) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
        try:
            return self.get_ip_address_strong()
        except Exception:
            return None

    def get_ssh_forward_port(self) -> TcpPort | None:
        return self.get_ssh_forward_port_path().load()

    def get_ssh_forward_port_path(self) -> VmMetaData.Parameter[TcpPort]:
        return self.__ssh_forward_port

    def set_ssh_forward_port(self, ssh_forward_port: TcpPort | int) -> None:
        self.get_ssh_forward_port_path().store(TcpPort(ssh_forward_port))

    def get_rdp_forward_port(self) -> TcpPort | None:
        return self.get_rdp_forward_port_path().load()

    def get_rdp_forward_port_path(self) -> VmMetaData.Parameter[TcpPort]:
        return self.__rdp_forward_port

    def set_rdp_forward_port(self, rdp_forward_port: TcpPort | int) -> None:
        self.get_rdp_forward_port_path().store(TcpPort(rdp_forward_port))

    def get_working_dir_path(self) -> pathlib.Path:
        return self.get_image_path().parent / "data"

    def get_platform(self) -> QemuPlatform:
        result = self.__platform.load()
        if not result:
            raise Exception("[Vm] Platform UNDEFINED")
        return result

    def get_vnc_display_port(self) -> TcpPort:
        result = self.__vnc_display_port.load()
        if not result:
            raise Exception("[Vm] VNC display port UNDEFINED")
        return result

    def makedirs(self) -> None:
        self.__image_path.makedirs()
        self.get_working_dir_path().mkdir(parents=True, exist_ok=True)
