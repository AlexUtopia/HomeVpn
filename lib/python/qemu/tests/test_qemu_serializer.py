import unittest

from lib.python.qemu import QemuSerializer


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
