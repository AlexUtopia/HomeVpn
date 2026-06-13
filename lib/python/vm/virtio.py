import urllib.request

from lib.python.logger import Logger
from lib.python.types import Path
from lib.python.vm import VmRegistry


# fixme utopia Переписать с использованием asyncio
# https://share.google/aimode/rGgH19qyDZ2coNdVp
class Virtio:
    __WIN_DRIVERS_FILENAME = "virtio-win-drivers.iso"
    DOWNLOAD_URL = "https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso"

    def __init__(self, vm_registry: VmRegistry):
        self.__vm_registry_path = vm_registry.get_path()

    def get_win_drivers(self) -> Path:
        win_drivers_iso_path = self.__get_win_drivers_iso_path()
        if win_drivers_iso_path.exists():
            Logger.instance().debug(f"[Virtio] Win drivers was downloaded: \"{win_drivers_iso_path}\"")
            return win_drivers_iso_path

        self.__download_win_drivers(win_drivers_iso_path)
        return win_drivers_iso_path

    def __get_win_drivers_iso_path(self) -> Path:
        self.__vm_registry_path.makedirs()
        return self.__vm_registry_path / Virtio.__WIN_DRIVERS_FILENAME

    def __download_win_drivers(self, win_drivers_iso_path: Path) -> None:
        Logger.instance().debug(
            f"[Virtio] Win drivers DOWNLOAD: {self.DOWNLOAD_URL} --> \"{win_drivers_iso_path}\"")
        urllib.request.urlretrieve(self.DOWNLOAD_URL, str(win_drivers_iso_path))
        Logger.instance().debug(f"[Virtio] Win drivers DOWNLOAD: OK")
