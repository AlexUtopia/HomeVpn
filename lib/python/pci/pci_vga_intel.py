from lib.python.system import CurrentOs
from lib.python.vm import VmMetaData

from lib.python.pci import BasePath, i915ovmfRom, LegacyVideoBiosRom, Pci, PciRom, VfioIgdPkgRom


# https://www.google.com/search?q=%D0%9F%D0%BE%D0%B4%D1%81%D0%BA%D0%B0%D0%B6%D0%B8%2C+%D0%BF%D0%BE%D0%B6%D0%B0%D0%BB%D1%83%D0%B9%D1%81%D1%82%D0%B0+%D1%80%D0%B5%D0%B6%D0%B8%D0%BC+%D0%BF%D1%80%D0%BE%D0%B1%D1%80%D0%BE%D1%81%D0%B0+UPT+%28%D0%BE%D0%BF%D0%B8%D1%81%D0%B0%D0%BD+%D0%B7%D0%B4%D0%B5%D1%81%D1%8C+https%3A%2F%2Fgithub.com%2Fqemu%2Fqemu%2Fcommit%2F0eb734241762bc63bf8308bed3573431f195ddcf%29+%D0%BC%D0%BE%D0%B6%D0%B5%D1%82+%D0%BE%D1%81%D1%83%D1%89%D0%B5%D1%81%D1%82%D0%B2%D0%BB%D1%8F%D1%82%D1%8C%D1%81%D1%8F+%D0%B2+%D1%80%D0%B5%D0%B6%D0%B8%D0%BC%D0%B0%D1%85%3A%0D%0A1%29+uefi+host%2C+uefi+guest%0D%0A2%29+uefi+host%2C+bios+guest%0D%0A3%29+bios+host%2C+bios+guest%0D%0A%3F&sca_esv=f8991862dc286373&sxsrf=APpeQnvNPwqYqCBhWM3k4EhBnD02IxUipg%3A1782243307179&source=hp&fbs=ABfTbFVoRrC-QTLMntAkgaY3Jlw1M0E9Cjhp1SXgJnQNWVrX06L8HC9MzKkTNiYdkaZdRzawK0FKI0u2fT5WSfLiPWVe4jK2sImDZVHjeep0OjuHEe3PhscDQn-ZYaNiwI0RNEMGthH94kF_ek3LYpBuS9lcmUaIlEUb84WwpAg_rngMHdIkW_2n_zojt9ygJiZTasX5-ICF8OAuUu0_hvcYSJMLH-pxzdV5s3y0Kkz3drlvWzN2NcdIWTBW6N78ihioJqO2VO-6FCIn86MXpNdBH2MoEEeP1g&aep=1&ntc=1&sa=X&ved=2ahUKEwiV1OjZjZ6VAxXSExAIHTnwKPgQ2J8OegQIDxAD&biw=1242&bih=554&dpr=1.1&mstk=AUtExfA21yc9umIS4rKxKKajTDoUcd-oHVotw6M3Rdd1WWfJpZcwOQ61gXxz33hcar8kI8_veqXYyccYcJ4QwdKjTF5u8jsYKtqGaRjO5KjFWmeBG2XM9lHkfPIAMN8rtNBp5oCkq5pdnyfTzZp8aEJ48hinE-qKUsXFlo6LCD8uDgsurRXONkc9Io9pEUKa3vdQ77TLjJkJHjViPrDYxp80ekqK9iKTzqfHkgiupwrsdHdP5hiAfu5qbwTmhKHHeZRJoyWJcJw5kLp8M1qanNF9JIqQPsUKY9zXhLcQ0Xk_BoEL3p1qUT-VqGfRcyFwt1kf_KJb8z_SgU8CAQ&csuir=1&mtid=7d86aqPNOfCk1fIPgaz02QY&lns_mode=cvst&udm=50

# | Параметры / режим проброса              | Legacy (BIOS host) | Legacy (UEFI host) | UPT (Universal PassThrough) | [Проект VfioIgdPkg](https://github.com/tomitamoeko/VfioIgdPkg) | [Проект i915ovmfPkg](https://github.com/x78x79x82x79/i915ovmfPkg) |
# | --------------------------------------- | ------------------ | ------------------ | --------------------------- | -------------------------------------------------------------- | ----------------------------------------------------------------- |
# | Host boot mode                          | BIOS               | UEFI               | UEFI                        | UEFI                                                           | UEFI                                                              |
# | Guest boot mode                         | BIOS (SeaBIOS)     | BIOS (SeaBIOS)     | UEFI (OVMF)                 | UEFI (OVMF)                                                    | UEFI (OVMF)                                                       |
# | Guest machine                           | i440fx             | i440fx             | q35                         | q35                                                            | q35                                                               |
# | CPU Intel                               | от [Sandy Bridge](https://github.com/qemu/qemu/commit/0eb734241762bc63bf8308bed3573431f195ddcf#diff-b3fe4475e398f3125e2c55e21d0415f1af31a4b19fc871cf27da615b2a7a36bfR41) | от [Sandy Bridge](https://github.com/qemu/qemu/commit/0eb734241762bc63bf8308bed3573431f195ddcf#diff-b3fe4475e398f3125e2c55e21d0415f1af31a4b19fc871cf27da615b2a7a36bfR41) | от [Broadwell](https://github.com/qemu/qemu/commit/0eb734241762bc63bf8308bed3573431f195ddcf#diff-b3fe4475e398f3125e2c55e21d0415f1af31a4b19fc871cf27da615b2a7a36bfR12) | от Sandy Bridge до Airmont без вывода на дисплей, начиная со Skylake (следующее за Airmont поколение) с выводом на дисплей (т.к. проектом поддерживается только OpRegion 2+ который появился со Skylake) | [Теоретический совместимо с Intel 14nm CPU (Sky Lake, Kaby Lake, Coffee Lake, Comet Lake)](https://github.com/x78x79x82x79/i915ovmfPkg/blob/master/README.md#current-feature-support) |
# | Параметр vfio-pci: addr                 | 0x02               | 0x02               | любой, кроме 0x02 [источник](https://github.com/qemu/qemu/commit/0eb734241762bc63bf8308bed3573431f195ddcf#diff-b3fe4475e398f3125e2c55e21d0415f1af31a4b19fc871cf27da615b2a7a36bfR85) | 0x02                                                           | 0x02                                                              |
# | Параметр vfio-pci: rombar               | 1                  | 1                  | 0                           | 1                                                              | 1                                                                 |
# | Параметр vfio-pci: romfile              | /sys/bus/pci/devices/0000:00:02.0/rom<br>Лучше извлечь из BIOS материнской платы чтобы заработал встроенный дисплей (LVDS) | Извлечь legacy video BIOS из UEFI материнской платы, если имеется (секция C5A4306E-E247-4ECD-A9D8-5B1985D3DCDA) | не требуется | vbios.rom собранный из исходников проекта | vbios.rom собранный из исходников проекта |
# | Параметр vfio-pci: x-igd-legacy-mode    | on                 | on                 | off                         | off                                                            | off                                                               |
# | Параметр vfio-pci: x-vga                | on                 | on                 | off                         | off                                                            | off                                                               |
# | Параметр vfio-pci: x-igd-opregion       | on                 | on                 | off (может быть on для вывода изображения на дисплей, см. [примечание](https://github.com/qemu/qemu/commit/0eb734241762bc63bf8308bed3573431f195ddcf#diff-b3fe4475e398f3125e2c55e21d0415f1af31a4b19fc871cf27da615b2a7a36bfR91)) | off | off |
# | Параметр vfio-pci: x-igd-lpc            | on                 | on                 | off                         | не применимо (только для i440fx)                               | не применимо (только для i440fx)                                  |
# | Параметр vfio-pci: x-igd-gms            | не применимо       | не применимо       | применить в зависимости от объёма ОЗУ вирт машины | не применимо                             | не применимо                                                      |
# | ОЗУ для вирт машины больше 2^32 байт    | -global i440FX-pcihost.pci-hole64-start=1024G | -global i440FX-pcihost.pci-hole64-start=1024G | использовать параметр x-igd-gms (1, 2, 4) | нет ограничений (при "Коде 43" нужен твик реестра гостя) | нет ограничений (при "Коде 43" нужен твик реестра гостя) |

# https://docs.google.com/document/d/1MR_KLy7nz1Ktc67QBPjZ5h5lPXRxRBRUF4c_w3FIN74/edit?usp=sharing
# https://docs.google.com/document/d/1AhgwXYXT8TtGgHSfp-qcTNiMvK4SUJ906DkQBy-PLKY/edit?usp=sharing

# https://github.com/gangqizai/igd

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
    def get_vfio_pci_options_table(self, vm_meta_data: VmMetaData):
        result = super().get_vfio_pci_options_table(vm_meta_data)

        if CurrentOs.is_bios_boot():
            if vm_meta_data.get_platform().is_i440fx_bios_boot():
                # Intel CPU Sandy Bridge+
                # Пробрасываемый GPU должен быть первичным (self.is_boot_vga())
                parameters = {
                    "addr": "0x02",
                    "rombar": 1,
                    "x-igd-legacy-mode": "on",
                    "x-vga": "on",
                    "x-igd-opregion": "on",
                    "x-igd-lpc": "on"
                }

                rom_file_path = LegacyVideoBiosRom(BasePath(vm_meta_data.get_platform().get_arch())).get_path()
                if not rom_file_path.exists():
                    rom_file_path = self.get_rom(vm_meta_data.get_working_dir_path())
                    if not rom_file_path.exists():
                        parameters["romfile"] = str(rom_file_path)
                    else:
                        print("Не удалось получить romfile из PCI - выходим")
                        return
                else:
                    parameters["romfile"] = str(rom_file_path)
                result.update(parameters)
            else:
                # Попробовать UPT
                raise Exception("[VgaPciIntel] Use only i440fx+bios with Intel integrated VGA")
        elif CurrentOs.is_uefi_boot():
            if vm_meta_data.get_platform().is_i440fx_bios_boot():
                # Intel CPU Sandy Bridge+
                parameters = {
                    "addr": "0x02",
                    "rombar": 1,
                    "x-igd-legacy-mode": "on",
                    "x-vga": "on",
                    "x-igd-opregion": "on",
                    "x-igd-lpc": "on"
                }

                rom_file_path = LegacyVideoBiosRom(BasePath(vm_meta_data.get_platform().get_arch())).get_path()
                if rom_file_path.exists():
                    parameters["romfile"] = str(rom_file_path)
                else:
                    print(
                        "Извлеки Video BIOS из UEFI материнской платы, ссылка на доку как это сделать + выход")
                    return
                result.update(parameters)
            elif vm_meta_data.get_platform().is_uefi_boot():
                mode = "UPT"
                if mode == "UPT":
                    # Intel CPU Broadwell+
                    parameters = {
                        "addr": "0x03",
                        "rombar": 0,
                        "x-igd-legacy-mode": "off",
                        "x-vga": "off",
                        "x-igd-opregion": "off",
                        "x-igd-lpc": "off"
                    }
                    # fixme utopia потенциально требуется вычисление x-igd-gms
                    #   /sys/kernel/debug/dri/0000:00:02.0/i915_capabilities
                elif mode == "UPT+opregion":
                    # Intel CPU Broadwell+
                    parameters = {
                        "addr": "0x03",
                        "rombar": 0,
                        "x-igd-legacy-mode": "off",
                        "x-vga": "off",
                        "x-igd-opregion": "on",
                        "x-igd-lpc": "off"
                    }
                elif mode == "VfioIgdPkg":
                    parameters = {
                        "addr": "0x02",
                        "rombar": 1,
                        "x-igd-legacy-mode": "off",
                        "x-vga": "off",
                        "x-igd-opregion": "off",
                        "x-igd-lpc": "off"
                    }
                    rom_file_no_video_path, rom_file_path, intel_gop_driver_file_path = VfioIgdPkgRom(
                        BasePath(vm_meta_data.get_platform().get_arch()), self.get_id()).get_paths()
                    if rom_file_path.exists():
                        parameters["romfile"] = str(rom_file_path)
                    elif rom_file_no_video_path.exists():
                        parameters["romfile"] = str(rom_file_no_video_path)
                    else:
                        raise Exception("[VgaPciIntel] VfioIgdPkg: Video BIOS (EFI) NOT FOUND\nBuild Video BIOS by instruction and try again")
                elif mode == "i915ovmfPkg":
                    parameters = {
                        "addr": "0x02",
                        "rombar": 1,
                        "x-igd-legacy-mode": "off",
                        "x-vga": "off",
                        "x-igd-opregion": "off",
                        "x-igd-lpc": "off"
                    }

                    rom_file_path = i915ovmfRom(
                        BasePath(vm_meta_data.get_platform().get_arch()), self.get_id()).get_path()
                    if rom_file_path.exists():
                        parameters["romfile"] = str(rom_file_path)
                    else:
                        raise Exception("[VgaPciIntel] i915ovmf: Video BIOS (EFI) NOT FOUND\nBuild Video BIOS by instruction and try again")
                else:
                    raise Exception("[VgaPciIntel] Unknown mode (UEFI)")
                result.update(parameters)

        return result

    def get_qemu_parameters(self, vm_meta_data):
        result = super().get_qemu_parameters(vm_meta_data)
        if len(result) > 0 and self.is_other_vga_disable():
            result.append({"-vga": "none"})
            # -mem-prealloc
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
