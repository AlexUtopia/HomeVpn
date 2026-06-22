from lib.python.pci import Pci


class VgaPciIntel(Pci):
    def __init__(self, pci):
        super().__init__()
        self._init(pci)
        self.__cpu = Cpu.get_cpu0()

    # https://pve.proxmox.com/wiki/PCI_Passthrough#%22BAR_3:_can't_reserve_[mem]%22_error
    def get_kernel_parameters(self):
        result = super().get_kernel_parameters()
        result.extend([{"module_blacklist": ["snd_hda_intel", "snd_hda_codec_hdmi"]},
                       {"video": {"efifb": "off", "vesafb": "off", "vesa": "off", "simplefb": "off"}},
                       {"l1tf": ["full", "force"]},
                       {"initcall_blacklist": "sysfb_init"}])
        return result

    # https://github.com/qemu/qemu/blob/master/docs/igd-assign.txt
    # https://www.reddit.com/r/VFIO/comments/i9dbyp/this_is_how_i_managed_to_passthrough_my_igd/
    # fixme utopia Проброс с OVMF + __VGA_PASSTHROUGH_MODE_UPT
    def get_vfio_pci_options_table(self, vm_meta_data):
        result = super().get_vfio_pci_options_table(vm_meta_data)

        if self.__check_passthrough_in_legacy_mode():
            result.update({"addr": "0x02", "rombar": 1, "x-vga": "on", "x-igd-opregion": "on"})

            rom_file_path = self.get_rom(vm_meta_data.get_working_dir_path())
            if rom_file_path is not None:
                result["romfile"] = rom_file_path

        else:
            result.update({"x-vga": "on", "x-igd-opregion": "on"})

        return result

    def get_qemu_parameters(self, vm_meta_data):
        result = super().get_qemu_parameters(vm_meta_data)
        if len(result) > 0 and self.is_other_vga_disable():
            result.append({"-vga": "none"})
            # result.append({"-fw_cfg": {"name": "opt/igd-opregion", "file": "/home/utopia/HomeVpn/opregion.bin"}})
            # result.append({"-fw_cfg": {"name": "opt/igd-bdsm-size", "file": "/home/utopia/HomeVpn/bdsmSize.bin"}})
            # result.append({"-machine": "pc-i440fx-2.2"})
            # result.append({"-device": { "vfio-pci-igd-lpc-bridge": { "addr": "0x1f" } }})
        return result

    def is_other_vga_disable(self):
        return True  # self.__check_passthrough_in_legacy_mode() # Идея не работает из-за невозможности запуска gtk

    def check_platform(self, qemu_platform):
        if self.__check_passthrough_in_legacy_mode():
            return
            if CurrentOs.is_bios_boot() and qemu_platform.is_i440fx_bios_boot():
                return

            recommendation = list()
            if not qemu_platform.is_i440fx_bios_boot():
                recommendation.append(f"use {qemu_platform.QEMU_PLATFORM_I440FX_BIOS}")
            if not CurrentOs.is_bios_boot():
                recommendation.append("OS must be boot in BIOS mode")
            raise Exception(
                f"[VgaPciIntel] Current platform NOT SUPPORTED for igd passthrough: {', '.join(recommendation)}")
        else:
            if CurrentOs.is_bios_boot() and qemu_platform.is_bios_boot():
                # Не знаю на чём проверить
                return
            if CurrentOs.is_uefi_boot() and qemu_platform.is_uefi_boot():
                # https://lore.kernel.org/all/20250312102929.329ff4f5.alex.williamson@redhat.com/T/
                # https://gitlab.com/qemu-project/qemu/-/issues/1538
                # Проверить на асере
                return
            if CurrentOs.is_uefi_boot() and qemu_platform.is_bios_boot():
                # Работает на асере
                return
            # fixme utopia Перепроверить с OVMF отсюда. Будет ли работать комбинация BIOS Host / UEFI Guest
            # https://github.com/x78x79x82x79/i915ovmfPkg
            # https://github.com/patmagauran/i915ovmfPkg

            if CurrentOs.is_bios_boot():
                raise Exception(
                    f"[VgaPciIntel] Current platform NOT SUPPORTED for igd passthrough: use {' or '.join(qemu_platform.get_bios_boot_platform_list())} platform")
            if CurrentOs.is_uefi_boot():
                raise Exception(
                    f"[VgaPciIntel] Current platform NOT SUPPORTED for igd passthrough: use {' or '.join(qemu_platform.get_uefi_boot_platform_list())} platform")

    @staticmethod
    def is_my_instance(pci: Pci):
        return pci.class_code.is_vga() and pci.device_id.is_intel()

    def __check_passthrough_in_legacy_mode(self):
        return True
        if self.__cpu.is_intel_above_broadwell():
            return False  # UPT passthrough
        elif self.__cpu.is_intel_above_sandybridge():
            return True  # Legacy passthrough
        raise Exception(f"[VgaPciIntel] Passthrough NOT SUPPORTED: old CPU \"{self.__cpu.get_uarch_codename()}\"")