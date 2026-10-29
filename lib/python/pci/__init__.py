"""PCI устройства, IOMMU группы и проброс в виртуальные машины."""

from .pci_address import PciAddress
from .pci_class_code import PciClassCode
from .pci_passthrough_mode import PciPassthroughMode
from .pci_vid_pid import PciVidPid
from .pci import Pci
from .intel_integrated_vga_generation import IntelIntegratedVgaGeneration
from .intel_integrated_vga_stolen_memory_size import IntelIntegratedVgaStolenMemorySize

from .pci_usb_controller import UsbEhciPci, UsbOhciPci, UsbUhciPci, UsbXhciPci

from .pci_device_rom import BasePath, Dmi, PlatformDescriptor, VfioIgdPkgRom, i915ovmfRom, LegacyVideoBiosRom
from .pci_vga_intel import VgaPciIntel

from .vfio_pci import VfioPci
from .vfio import Vfio

__all__ = ["BasePath",
           "Dmi",
           "IntelIntegratedVgaGeneration",
           "IntelIntegratedVgaStolenMemorySize",
           "LegacyVideoBiosRom",
           "Pci",
           "PciAddress",
           "PciClassCode",
           "PciPassthroughMode",
           "PciVidPid",
           "PlatformDescriptor",
           "UsbEhciPci",
           "UsbOhciPci",
           "UsbUhciPci",
           "UsbXhciPci",
           "Vfio",
           "VfioIgdPkgRom",
           "VfioPci",
           "VgaPciIntel",
           "i915ovmfRom"]
