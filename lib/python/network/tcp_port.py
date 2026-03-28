
class TcpPort:
    TCP_PORT_MIN = 1
    TCP_PORT_MAX = 65535

    SSH_PORT_DEFAULT = 22
    DNS_PORT_DEFAULT = 53
    RDP_PORT_DEFAULT = 3389
    VNC_BASE_PORT_NUMBER = 5900

    def __init__(self, port: int | str):
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
        return int(self) == int(TcpPort(other))

    def is_ssh(self) -> bool:
        return int(self) == TcpPort.SSH_PORT_DEFAULT

    def is_rdp(self) -> bool:
        return int(self) == TcpPort.RDP_PORT_DEFAULT

    def is_vnc_base(self) -> bool:
        return int(self) == TcpPort.VNC_BASE_PORT_NUMBER

    @staticmethod
    def is_valid(port: int | str) -> bool:
        try:
            port_as_int = int(port)
            if port_as_int < TcpPort.TCP_PORT_MIN:
                return False
            if port_as_int > TcpPort.TCP_PORT_MAX:
                return False

            return True
        except Exception:
            return False