class QemuRtc:
    def __init__(self):
        pass

    def get_qemu_parameters(self) -> dict:
        return {"-rtc": {"base": "localtime", "clock": "host"}}