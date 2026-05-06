import pathlib


# https://forum.proxmox.com/threads/laptop-keyboard-touchpad-passthough-to-a-vm.135399/
# qemu-system-$(uname -m) -object input-linux,help
# Тачпад ведёт себя не адекватно поэтому не пробрасываем его
class QemuBuiltinKeyboardAndMousePassthrough:
    INPUT_DEV_PATH = pathlib.Path("/dev/input/by-path")

    def __init__(self):
        self.__table = {"kbd": {"grab_all": "on", "repeat": "on"}}  # "mouse": {},

    def get_qemu_parameters(self) -> list[dict]:
        result = []
        for target, additional_args in self.__table.items():
            result.extend(self.__get_qemu_parameters(target, additional_args))
        return result

    def __get_qemu_parameters(self, target: str, additional_args: dict[str, str]) -> list[dict]:
        result = []
        index = 0
        for path in self.INPUT_DEV_PATH.glob(f"platform-*-event-{target}"):
            args = {"id": f"{target}{index}", "evdev": path}
            args.update(additional_args)
            result.append({"-object": {"input-linux": args}})
            index = index + 1
        return result
