from lib.python.vm import VmMetaData


class QemuDiskVirtio:
    def __init__(self, vm_meta_data: VmMetaData):
        self.__vm_meta_data = vm_meta_data

    def get_qemu_parameters(self) -> list[dict]:
        return [{"-drive": {"file": self.__vm_meta_data.get_image_path(),
                            "media": "disk", "if": "virtio"}}]
