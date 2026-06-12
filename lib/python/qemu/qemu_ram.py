import psutil


class QemuRam:
    DEFAULT = 4096
    BYTES_IN_MIBIBYTE = 1024 * 1024

    def __init__(self, ram_size_in_mib: int = DEFAULT):
        self.__ram_size_in_mib = int(ram_size_in_mib)
        if self.__ram_size_in_mib <= 0:
            self.__ram_size_in_mib = self.DEFAULT
        self.check()

    def __str__(self):
        return str(self.__ram_size_in_mib)

    def __repr__(self):
        return self.__str__()

    def get_qemu_parameters(self) -> dict:
        return {"-m": self.__ram_size_in_mib}

    def check(self):
        mem = psutil.virtual_memory()
        size_in_bytes = self.__ram_size_in_mib * self.BYTES_IN_MIBIBYTE
        if size_in_bytes > mem.available:
            raise Exception(
                f"[Ram] Vm RAM size FAIL: required={size_in_bytes} (bytes), available={mem.available} (bytes)")
