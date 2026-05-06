from lib.python.utils import UInt16Hex


# https://pcisig.com/sites/default/files/files/PCI_Code-ID_r_1_11__v24_Jan_2019.pdf
class PciClassCode(UInt16Hex):
    BASE_CLASS_BACKWARD_COMPATIBILITY = 0x00
    BASE_CLASS_BACKWARD_COMPATIBILITY_ALL_EXCEPT_VGA = 0x00
    BASE_CLASS_BACKWARD_COMPATIBILITY_VGA = 0x01
    BASE_CLASS_VGA = 0x03

    BASE_CLASS_MULTIMEDIA_DEVICE = 0x04
    BASE_CLASS_MULTIMEDIA_DEVICE_VIDEO_VENDOR_SPECIFIC = 0x00
    BASE_CLASS_MULTIMEDIA_DEVICE_AUDIO_VENDOR_SPECIFIC = 0x01
    BASE_CLASS_MULTIMEDIA_DEVICE_COMPUTER_TELEPHONY_VENDOR_SPECIFIC = 0x02
    BASE_CLASS_MULTIMEDIA_DEVICE_HIGH_DEFINITION_AUDIO_V1 = 0x03
    BASE_CLASS_MULTIMEDIA_DEVICE_OTHER_VENDOR_SPECIFIC = 0x80

    BASE_CLASS_BRIDGE_DEVICE = 0x06
    BASE_CLASS_BRIDGE_DEVICE_HOST = 0x00
    BASE_CLASS_BRIDGE_DEVICE_ISA = 0x01
    BASE_CLASS_BRIDGE_DEVICE_EISA = 0x02
    BASE_CLASS_BRIDGE_DEVICE_MCA = 0x03
    BASE_CLASS_BRIDGE_DEVICE_PCI_TO_PCI = 0x04
    BASE_CLASS_BRIDGE_DEVICE_PCMCIA = 0x05
    BASE_CLASS_BRIDGE_DEVICE_NU_BUS = 0x06
    BASE_CLASS_BRIDGE_DEVICE_CARD_BUS = 0x07
    BASE_CLASS_BRIDGE_DEVICE_RACE_WAY = 0x08
    BASE_CLASS_BRIDGE_DEVICE_SEMI_TRANSPARENT_PCI_TO_PCI = 0x09
    BASE_CLASS_BRIDGE_DEVICE_INFINIBAND_TO_PCI = 0x0A

    BASE_CLASS_SERIAL_BUS_CONTROLLER = 0x0C
    BASE_CLASS_SERIAL_BUS_CONTROLLER_IEEE1394 = 0x00
    BASE_CLASS_SERIAL_BUS_CONTROLLER_ACCESS = 0x01
    BASE_CLASS_SERIAL_BUS_CONTROLLER_SSA = 0x02
    BASE_CLASS_SERIAL_BUS_CONTROLLER_USB = 0x03
    BASE_CLASS_SERIAL_BUS_CONTROLLER_USB_UHCI = 0x00
    BASE_CLASS_SERIAL_BUS_CONTROLLER_USB_OHCI = 0x10
    BASE_CLASS_SERIAL_BUS_CONTROLLER_USB_EHCI = 0x20
    BASE_CLASS_SERIAL_BUS_CONTROLLER_USB_XHCI = 0x30
    BASE_CLASS_SERIAL_BUS_CONTROLLER_USB_WITHOUT_SPECIFIC_PROG_IF = 0x80
    BASE_CLASS_SERIAL_BUS_CONTROLLER_USB_DEVICE = 0xFE
    BASE_CLASS_SERIAL_BUS_CONTROLLER_SMBUS = 0x05
    BASE_CLASS_SERIAL_BUS_CONTROLLER_CAN = 0x09

    def __new__(cls, class_code=0):
        return super(PciClassCode, cls).__new__(cls, class_code)

    def get_base_class(self):
        return (self.__int__() >> BitUtils.BITS_IN_BYTE) & BitUtils.LSB_TETRAD_MASK

    def get_sub_class(self):
        return self.__int__() & BitUtils.LSB_TETRAD_MASK

    # https://github.com/xiaoran007/pypci/blob/v0.0.4/src/pypci/backend/pci.py#L74
    def is_vga(self):
        return self.get_base_class() == self.BASE_CLASS_VGA or (
                self.get_base_class() == self.BASE_CLASS_BACKWARD_COMPATIBILITY and self.get_sub_class() == self.BASE_CLASS_BACKWARD_COMPATIBILITY_VGA)

    def is_audio(self):
        return (self.get_base_class() == self.BASE_CLASS_MULTIMEDIA_DEVICE) and (
                self.get_sub_class() == self.BASE_CLASS_MULTIMEDIA_DEVICE_HIGH_DEFINITION_AUDIO_V1)

    def is_usb_host_controller(self, prog_if):
        return self.is_usb_uhci_controller(prog_if) or self.is_usb_ohci_controller(
            prog_if) or self.is_usb_ehci_controller(prog_if) or self.is_usb_xhci_controller(prog_if)

    def is_usb_uhci_controller(self, prog_if):
        return self.is_usb() and (
                prog_if == self.BASE_CLASS_SERIAL_BUS_CONTROLLER_USB_UHCI)

    def is_usb_ohci_controller(self, prog_if):
        return self.is_usb() and (
                prog_if == self.BASE_CLASS_SERIAL_BUS_CONTROLLER_USB_OHCI)

    def is_usb_ehci_controller(self, prog_if):
        return self.is_usb() and (
                prog_if == self.BASE_CLASS_SERIAL_BUS_CONTROLLER_USB_EHCI)

    def is_usb_xhci_controller(self, prog_if):
        return self.is_usb() and (
                prog_if == self.BASE_CLASS_SERIAL_BUS_CONTROLLER_USB_XHCI)

    def is_usb(self):
        return (self.get_base_class() == self.BASE_CLASS_SERIAL_BUS_CONTROLLER) and (
                self.get_sub_class() == self.BASE_CLASS_SERIAL_BUS_CONTROLLER_USB)

    def is_isa_bridge(self):
        return (self.get_base_class() == self.BASE_CLASS_BRIDGE_DEVICE) and (
                self.get_sub_class() == self.BASE_CLASS_BRIDGE_DEVICE_ISA)
