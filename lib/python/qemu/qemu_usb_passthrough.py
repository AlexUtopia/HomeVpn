import typing


# Клавиатура Microsoft # Natural Ergonomic Keyboard 4000 v 1.0
# USB-Bluetooth 5.0 адаптер Ugreen # CM390
# Мышка Logitec # B110
# Клавиатура с тачпадом Harper # KBT-330
class QemuUsbPassthrough:
    def __init__(self, usb_id_list: list[tuple[int, int]] = [(0x045e, 0x00db), (0x0bda, 0x8771), (0x046d, 0xc05b),
                                                             (0x258a, 0x0302)]):
        self.__usb_id_list = usb_id_list

    def get_qemu_parameters(self) -> list[typing.Any]:
        if not self.__usb_id_list:
            return []

        result = ["-usb"]

        for vid, pid in self.__usb_id_list:
            result.append({"-device": ["usb-host", {"vendorid": f"0x{vid:04X}", "productid": f"0x{pid:04X}"}]})
        return result
