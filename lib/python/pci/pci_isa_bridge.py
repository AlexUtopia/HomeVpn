from lib.python.pci import Pci


class IsaBridgePci(Pci):
    def __init__(self, pci):
        super().__init__()
        self._init(pci)

    @staticmethod
    def is_my_instance(pci: Pci):
        return pci.class_code.is_isa_bridge()
