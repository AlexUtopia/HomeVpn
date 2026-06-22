from lib.python.pci import Pci


class UsbUhciPci(Pci):
    def __init__(self, pci):
        super().__init__()
        self._init(pci)

    def get_kernel_parameters(self):
        return ["usbcore.nousb"]

    @staticmethod
    def is_my_instance(pci):
        return pci.class_code.is_usb_uhci_controller(pci.prog_if)


class UsbOhciPci(Pci):
    def __init__(self, pci):
        super().__init__()
        self._init(pci)

    def get_kernel_parameters(self):
        return ["usbcore.nousb"]

    @staticmethod
    def is_my_instance(pci):
        return pci.class_code.is_usb_ohci_controller(pci.prog_if)


class UsbEhciPci(Pci):
    def __init__(self, pci):
        super().__init__()
        self._init(pci)

    def get_kernel_parameters(self):
        return ["usbcore.nousb"]

    @staticmethod
    def is_my_instance(pci):
        return pci.class_code.is_usb_ehci_controller(pci.prog_if)


class UsbXhciPci(Pci):
    def __init__(self, pci):
        super().__init__()
        self._init(pci)

    def get_kernel_parameters(self):
        return ["usbcore.nousb"]

    @staticmethod
    def is_my_instance(pci):
        return pci.class_code.is_usb_xhci_controller(pci.prog_if)
