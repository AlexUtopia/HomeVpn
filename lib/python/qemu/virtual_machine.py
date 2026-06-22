import subprocess

from lib.python.logger import Logger
from lib.python.network import NetworkBridge
from lib.python.pci import VfioPci
from lib.python.vm import VmMetaData

from lib.python.qemu import QemuAccel, QemuBuiltinKeyboardAndMousePassthrough, QemuCdRom, QemuCpu, QemuDiskVirtio, \
    QemuLogging, QemuPlatform, QemuRam, QemuRtc, QemuSerial, QemuSerializer, QemuUsbPassthrough, QemuVgaDefault, \
    QemuVgaVirtio


# fixme utopia Обеспечить возможность установки win11 (в том числе win11 arm)
# https://serverfault.com/a/1096401/1120954
# https://extralan.ru/?p=3060
# secure-boot check win11
# https://www.iobit.com/en/knowledge-how-to-enable-secure-boot-on-windows--355.php
class VirtualMachine:
    def __init__(self, network_bridge,
                 vm_meta_data: VmMetaData,
                 qemu_accel: QemuAccel | None = None,
                 qemu_builtin_kbd_and_mouse_passthrough: QemuBuiltinKeyboardAndMousePassthrough | None = None,
                 qemu_cdrom: QemuCdRom | None = None,
                 qemu_cpu: QemuCpu | None = None,
                 qemu_disk: QemuDiskVirtio | None = None,
                 qemu_logging: QemuLogging | None = None,
                 qemu_ram: QemuRam | None = None,
                 qemu_rtc: QemuRtc | None = None,
                 qemu_serial: QemuSerial | None = None,
                 qemu_usb_passthrough: QemuUsbPassthrough | None = None,
                 qemu_vga: QemuVgaDefault | QemuVgaVirtio | None = None,
                 vfio_pci: VfioPci | None = None):
        self.__tap = Tap()
        self.__network_bridge = network_bridge
        self.__vm_meta_data = vm_meta_data
        self.__qemu_accel = qemu_accel if qemu_accel else QemuAccel(vm_meta_data)
        self.__qemu_builtin_kbd_and_mouse_passthrough = qemu_builtin_kbd_and_mouse_passthrough
        self.__qemu_cdrom = qemu_cdrom if qemu_cdrom else QemuCdRom()
        self.__qemu_cpu = qemu_cpu if qemu_cpu else QemuCpu()
        self.__qemu_disk = qemu_disk if qemu_disk else QemuDiskVirtio(vm_meta_data)
        self.__qemu_logging = qemu_logging if qemu_logging else QemuLogging(vm_meta_data)
        self.__qemu_platform = QemuPlatform(self.__vm_meta_data)
        self.__qemu_ram = qemu_ram if qemu_ram else QemuRam()
        self.__qemu_rtc = qemu_rtc if qemu_rtc else QemuRtc()
        self.__qemu_serial = qemu_serial
        self.__qemu_usb_passthrough = qemu_usb_passthrough
        self.__qemu_vga = qemu_vga if qemu_vga else QemuVgaDefault()
        self.__vfio_pci = vfio_pci
        self.__serializer = QemuSerializer()

    def run(self):
        self.__network_bridge.create()

        with self.__qemu_platform as _:
            command_line = self.__command_line()
            Logger.instance().debug(f"[Vm] Run cmd: {command_line}")
            result = subprocess.run(command_line, shell=True, capture_output=True, text=True)
            Logger.instance().debug(f"[Vm] Run result:\nSTDOUT\n{result.stdout}\nSTDERR\n{result.stderr}\n")


    def __command_line(self):
        command_parts_list = [self.__serialize(self.__qemu_accel,
                                               self.__qemu_builtin_kbd_and_mouse_passthrough,
                                               self.__qemu_cdrom,
                                               self.__qemu_cpu,
                                               self.__qemu_disk,
                                               self.__qemu_logging,
                                               self.__qemu_platform,
                                               self.__qemu_ram,
                                               self.__qemu_rtc,
                                               self.__qemu_serial,
                                               self.__qemu_usb_passthrough
                                               ),
                              self.__network(),
                              self.__other(),
                              self.__get_qemu_vga_command_line(),
                              self.__qemu_pci_passthrough_command_line(),
                              self.__monitor()
                              ]
        return " ".join(command_parts_list)

    def __qemu_command_line(self):
        return f"qemu-system-{self.__vm_meta_data.get_platform().get_arch()}"

    def __serialize(self, *args) -> str:
        result : list[str] = []
        for it in args:
            if it:
                result.append(self.__serializer.serialize(it.get_qemu_parameters()))
        return " ".join(result)


    def __network(self):
        self.__tap.create()
        self.__network_bridge.add_and_configure_tap(self.__tap, self.__vm_meta_data)

        tap_name = str(self.__tap)
        netdev_id = "{}-id".format(tap_name)

        # fixme utopia Присвоим ip адрес vm через mac адрес
        # https://superuser.com/questions/1413011/setting-a-static-ip-upon-qemu-vm-creation

        return "-netdev tap,ifname={0},script=no,downscript=no,id={1} -device virtio-net,netdev={1},mac={2},addr=0x3".format(
            tap_name, netdev_id, self.__vm_meta_data.get_mac_address_as_string())


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

    def __get_qemu_vga_command_line(self):
        if self.__vfio_pci is not None and self.__vfio_pci.is_other_vga_disable():
            return ""
        return self.__serializer.serialize(self.__qemu_vga.get_qemu_parameters())

    def __qemu_pci_passthrough_command_line(self):
        if self.__vfio_pci is None:
            return ""
        self.__vfio_pci.check_platform(self.__qemu_platform)
        return self.__serializer.serialize(self.__vfio_pci.get_qemu_parameters(self.__vm_meta_data))
