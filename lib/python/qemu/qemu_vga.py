
# https://www.qemu.org/docs/master/system/devices/virtio-gpu.html
# https://www.qemu.org/docs/master/system/invocation.html#hxtool-3
# https://wiki.archlinux.org/title/QEMU#virtio
# https://wiki.archlinux.org/title/QEMU/Guest_graphics_acceleration#Virgil3d_virtio-gpu_paravirtualized_device_driver
# https://github.com/virtio-win/kvm-guest-drivers-windows/pull/943
# Полноценно работает только для Linux guest, для Windows guest отсутствуют драйвера для virtio-gpu
class QemuVgaVirtio:
    def __init__(self):
        pass

    def get_qemu_parameters(self) -> list[dict]:
        return [{"-device": "virtio-vga-gl", "-display": {"sdl": {"gl": "on"}}}]


class QemuVgaDefault:
    def __init__(self):
        pass

    def get_qemu_parameters(self) -> list[dict]:
        return [{"-vga": "std", "-display": {"gtk": {}}}]