import os
import pathlib


class QemuCdRom:
    OS_DISTR_INDEX = 0
    VIRTIO_WIN_DRIVERS_INDEX = 1
    HW_CDROM_INDEX = 2

    def __init__(self, os_distr_path: str | os.PathLike[str] | None = None,
                 virtio_win_drivers_path: str | os.PathLike[str] | None = None,
                 hw_cdrom_path: str | os.PathLike[str] | None = pathlib.Path("/dev/sr0")):
        self.__table = {self.OS_DISTR_INDEX: os_distr_path,
                        self.VIRTIO_WIN_DRIVERS_INDEX: virtio_win_drivers_path,
                        self.HW_CDROM_INDEX: hw_cdrom_path}

    def get_qemu_parameters(self) -> list[dict]:
        result = []
        for index, path in self.__table.items():
            qemu_parameters_item = self.__get_qemu_parameters_template(index, path)
            if qemu_parameters_item:
                result.append(qemu_parameters_item)
        return result

    def __get_qemu_parameters_template(self, index: int, path: str | os.PathLike[str] | None) -> dict | None:
        if not path:
            return None

        if not pathlib.Path(path).exists():
            return None

        return {"-drive": {"file": str(path), "media": "cdrom", "if": "ide", "index": index}}
