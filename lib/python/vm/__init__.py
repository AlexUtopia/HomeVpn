"""Виртуальные машины: метаданные, реестр и устройства."""

from .platform import QemuPlatform

from .vm_name import VmName
from .vm_meta_data import VmMetaData
from .vm_registry import VmRegistry

from .virtio import Virtio

__all__ = ["QemuPlatform",
           "Virtio",
           "VmMetaData",
           "VmName",
           "VmRegistry"]
