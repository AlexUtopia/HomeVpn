import typing

from lib.python.logger import Logger
from lib.python.system import CurrentOs
from lib.python.types import Path
from lib.python.vm import VmMetaData

from lib.python.pci import BasePath, i915ovmfRom, IntelIntegratedVgaGeneration, IntelIntegratedVgaStolenMemorySize, \
    LegacyVideoBiosRom, Pci, VfioIgdPkgRom

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
    """Встроенная графика Intel (IGD, Integrated Graphics Device)

    .. note::
       IGD — не "чистое" PCI устройство: оно использует дополнительные области
       памяти (OpRegion, Data Stolen Memory) и зависит от чипсета и BIOS.
       Подробности и матрица режимов проброса:
       https://github.com/qemu/qemu/blob/master/docs/igd-assign.txt
    """

    def __init__(self, pci: Pci):
        super().__init__()
        self._init(pci)

    def get_kernel_parameters(self) -> list[dict[str, typing.Any]]:
        """Получить параметры ядра хоста для проброса IGD

        :return: Список параметров ядра

        .. note::
           Драйвер i915 и звуковые драйверы HDMI на хосте блокируются, чтобы
           не занимать устройство до передачи его в виртуальную машину

        .. seealso::
           https://pve.proxmox.com/wiki/PCI_Passthrough#%22BAR_3:_can't_reserve_[mem]%22_error
        """
        result = super().get_kernel_parameters()
        result.extend([{"module_blacklist": ["snd_hda_intel", "snd_hda_codec_hdmi"]},
                       {"video": {"efifb": "off", "vesafb": "off", "vesa": "off", "simplefb": "off"}},
                       {"l1tf": ["full", "force"]},
                       {"initcall_blacklist": "sysfb_init"}])
        return result

    def get_vfio_pci_options_table(self, vm_meta_data: VmMetaData) -> tuple[
            dict[str, typing.Any], list[dict[str, typing.Any]]]:
        """Получить параметры проброса IGD для QEMU

        :param vm_meta_data: Метаданные виртуальной машины
        :return: Кортеж из параметров устройства ``vfio-pci`` и дополнительных
                 параметров QEMU, которые добавляются вне блока ``-device``

        .. note::
           Режим проброса берётся из :class:`VmMetaData.IgdPassthroughMode`;
           значение ``default`` раскрывается по платформе гостя и режиму
           загрузки хоста

        .. seealso::
           https://github.com/qemu/qemu/blob/master/docs/igd-assign.txt
        """
        vfio_pci_options_table, qemu_parameters = super().get_vfio_pci_options_table(vm_meta_data)

        mode = self.__get_passthrough_mode(vm_meta_data)
        vfio_pci_options_table.update(self.__get_vfio_pci_options_table_by_mode(mode, vm_meta_data))
        qemu_parameters.extend(self.__get_qemu_parameters_by_mode(mode))

        return vfio_pci_options_table, qemu_parameters

    @staticmethod
    def is_my_instance(pci: Pci) -> bool:
        """Проверить, что PCI устройство является встроенной графикой Intel

        :param pci: PCI устройство
        :return: ``True``, если устройство — VGA-контроллер Intel
        """
        return pci.class_code.is_vga() and pci.device_id.is_intel()

    def __get_passthrough_mode(self, vm_meta_data: VmMetaData) -> VmMetaData.IgdPassthroughMode:
        """Определить режим проброса IGD

        :param vm_meta_data: Метаданные виртуальной машины
        :return: Режим проброса

        .. note::
           Если в метаданных ВМ режим не задан (``default``), он выбирается
           по платформе гостя и режиму загрузки хоста
        """
        mode = vm_meta_data.get_igd_passthrough_mode()
        if mode is VmMetaData.IgdPassthroughMode.DEFAULT:
            return self.__get_default_passthrough_mode(vm_meta_data)
        return mode

    def __get_default_passthrough_mode(self, vm_meta_data: VmMetaData) -> VmMetaData.IgdPassthroughMode:
        """Раскрыть режим ``default`` по платформе гостя и режиму загрузки хоста

        :param vm_meta_data: Метаданные виртуальной машины
        :return: Режим проброса
        :raises Exception: Если комбинация гостевой платформы и режима загрузки хоста не поддерживается

        .. note::
           Для гостя с BIOS (i440fx) выбирается Legacy, если есть legacy Video BIOS,
           иначе UPT. Для UEFI гостя на UEFI хосте выбирается VfioIgdPkg
        """
        platform = vm_meta_data.get_platform()
        if platform.is_i440fx_bios_boot():
            # Гостевая ОС грузится через BIOS (SeaBIOS), хост может грузиться как через BIOS, так и через UEFI
            if self.__get_legacy_video_bios_rom_path(vm_meta_data).exists():
                # Video BIOS (legacy) есть - legacy режим (Intel CPU Sandy Bridge to Comet Lake)
                return VmMetaData.IgdPassthroughMode.LEGACY
            # Video BIOS (legacy) нет - UPT режим (Intel CPU Broadwell+)
            return VmMetaData.IgdPassthroughMode.UPT
        if platform.is_uefi_boot() and CurrentOs.is_uefi_boot():
            # UEFI гость на UEFI хосте - пробрасываем готовый Video BIOS (EFI)
            return VmMetaData.IgdPassthroughMode.VFIO_IGD_PKG
        raise Exception(
            f"[VgaPciIntel] Passthrough mode UNDEFINED for guest platform \"{platform.get_machine()}\" and host boot "
            f"mode. Set \"igd_passthrough_mode\" in vm metadata")

    @staticmethod
    def __get_legacy_video_bios_rom_path(vm_meta_data: VmMetaData) -> Path:
        """Получить путь к legacy Video BIOS платформы

        :param vm_meta_data: Метаданные виртуальной машины
        :return: Путь к ROM-файлу (файл может не существовать)

        .. note::
           Наличие файла определяет выбор Legacy режима при раскрытии ``default``
        """
        return LegacyVideoBiosRom(VgaPciIntel.__get_base_path(vm_meta_data)).get_path()

    def __get_vfio_pci_options_table_by_mode(self, mode: VmMetaData.IgdPassthroughMode,
                                             vm_meta_data: VmMetaData) -> dict[str, typing.Any]:
        """Получить параметры устройства ``vfio-pci`` для режима проброса

        :param mode: Режим проброса
        :param vm_meta_data: Метаданные виртуальной машины
        :return: Параметры устройства ``vfio-pci``
        :raises Exception: Если режим не поддерживается поколением GPU или неизвестен

        .. note::
           Перед построением параметров проверяется применимость режима
           к поколению GPU
        """
        self.__check_passthrough_mode_supported(mode)

        if mode is VmMetaData.IgdPassthroughMode.UPT:
            return self.__get_upt_options_table()
        if mode is VmMetaData.IgdPassthroughMode.UPT_OPREGION:
            return self.__get_upt_opregion_options_table()
        if mode is VmMetaData.IgdPassthroughMode.LEGACY:
            return self.__get_legacy_options_table(vm_meta_data)
        if mode is VmMetaData.IgdPassthroughMode.VFIO_IGD_PKG:
            return self.__get_vfio_igd_pkg_options_table(vm_meta_data)
        if mode is VmMetaData.IgdPassthroughMode.I915OVMF_PKG:
            return self.__get_i915ovmf_pkg_options_table(vm_meta_data)
        raise Exception(f"[VgaPciIntel] Unknown passthrough mode \"{mode}\"")

    def __check_passthrough_mode_supported(self, mode: VmMetaData.IgdPassthroughMode) -> None:
        """Проверить применимость режима проброса к поколению GPU

        :param mode: Режим проброса
        :raises Exception: Если режим не поддерживается поколением GPU

        .. note::
           UPT требует Intel CPU Broadwell+, Legacy — Intel CPU Sandy Bridge
           to Comet Lake. Для режимов с готовым Video BIOS (EFI) проверка
           поколения не выполняется
        """
        generation = IntelIntegratedVgaGeneration.from_pci(self)

        if mode is VmMetaData.IgdPassthroughMode.UPT or mode is VmMetaData.IgdPassthroughMode.UPT_OPREGION:
            if generation.is_upt_supported():
                return
            raise Exception(f"[VgaPciIntel] UPT passthrough NOT SUPPORTED for GPU \"{generation}\": "
                            f"Intel CPU Broadwell+ required")

        if mode is VmMetaData.IgdPassthroughMode.LEGACY:
            if generation.is_legacy_supported():
                return
            raise Exception(f"[VgaPciIntel] Legacy passthrough NOT SUPPORTED for GPU \"{generation}\": "
                            f"Intel CPU Sandy Bridge to Comet Lake required")

    @staticmethod
    def __get_qemu_parameters_by_mode(mode: VmMetaData.IgdPassthroughMode) -> list[dict[str, typing.Any]]:
        """Получить дополнительные параметры QEMU для режима проброса

        :param mode: Режим проброса
        :return: Список дополнительных параметров QEMU

        .. note::
           ``-vga none`` взводится только для НЕ-UPT режимов: в UPT пробрасываемый
           GPU не является первичным VGA, поэтому прочие VGA отключать не нужно
        """
        if mode is VmMetaData.IgdPassthroughMode.UPT or mode is VmMetaData.IgdPassthroughMode.UPT_OPREGION:
            return []
        return [{"-vga": "none"}]

    def __get_x_igd_gms(self) -> int | None:
        """Получить значение параметра QEMU ``x-igd-gms``

        :return: Значение поля GMS или ``None``, если его нельзя определить

        .. note::
           Для поколений с неизвестным форматом регистра GGC (например,
           Lunar Lake) параметр не взводится: QEMU всё равно не сможет его
           применить

        .. note::
           Если регистр GGC недоступен для чтения (например, нет прав root),
           параметр не взводится, а в лог пишется предупреждение. Поведение
           при этом не меняется: значение по умолчанию (``x-igd-gms=0``)
           означает "использовать значение хоста"
        """
        generation = IntelIntegratedVgaGeneration.from_pci(self)
        if not generation.is_stolen_memory_size_supported():
            return None

        try:
            return IntelIntegratedVgaStolenMemorySize.get(self).get_gms()
        except Exception as error:
            Logger.instance().warning(error)
            return None

    def __get_upt_options_table(self) -> dict[str, typing.Any]:
        """Получить параметры устройства ``vfio-pci`` для режима UPT

        :return: Параметры устройства ``vfio-pci``

        .. note::
           UPT поддерживается начиная с Intel CPU Broadwell. Видеопамять
           (Data Stolen Memory) не требуется, поэтому ROM BAR выключен
           (``rombar=0``), а VGA-диапазоны не пробрасываются (``x-vga=off``)

        .. note::
           Параметр ``x-igd-gms`` заполняется значением поля GMS из регистра
           GGC HostBridge, если поколение GPU позволяет его вычислить

        .. seealso::
           https://github.com/qemu/qemu/commit/0eb734241762bc63bf8308bed3573431f195ddcf
        """
        result = {"addr": "0x03",
                  "rombar": 0,
                  "x-igd-legacy-mode": "off",
                  "x-vga": "off",
                  "x-igd-opregion": "off",
                  "x-igd-lpc": "off"}

        x_igd_gms = self.__get_x_igd_gms()
        if x_igd_gms is not None:
            result["x-igd-gms"] = x_igd_gms

        return result

    def __get_upt_opregion_options_table(self) -> dict[str, typing.Any]:
        """Получить параметры устройства ``vfio-pci`` для режима UPT+OpRegion

        :return: Параметры устройства ``vfio-pci``

        .. note::
           Отличается от UPT только включённым ``x-igd-opregion``. OpRegion нужен
           для вывода изображения на физический дисплей
        """
        result = self.__get_upt_options_table()
        result["x-igd-opregion"] = "on"
        return result

    def __get_legacy_options_table(self, vm_meta_data: VmMetaData) -> dict[str, typing.Any]:
        """Получить параметры устройства ``vfio-pci`` для режима Legacy

        :param vm_meta_data: Метаданные виртуальной машины
        :return: Параметры устройства ``vfio-pci``
        :raises Exception: Если гостевая платформа не i440fx или Video BIOS не найден

        .. note::
           Legacy поддерживается для Intel CPU Sandy Bridge to Comet Lake
           и требует гостевую платформу i440fx. Пробрасываемый GPU должен быть
           первичным (``is_boot_vga()``)

        .. note::
           Параметр ``x-igd-gms`` заполняется значением поля GMS из регистра
           GGC HostBridge, если поколение GPU позволяет его вычислить
        """
        platform = vm_meta_data.get_platform()
        if not platform.is_i440fx_bios_boot():
            raise Exception(
                f"[VgaPciIntel] Legacy passthrough NOT SUPPORTED for guest platform \"{platform.get_machine()}\"")

        result = {"addr": "0x02",
                  "rombar": 1,
                  "x-igd-legacy-mode": "on",
                  "x-vga": "on",
                  "x-igd-opregion": "on",
                  "x-igd-lpc": "on",
                  "romfile": str(self.__get_legacy_rom_file_path(vm_meta_data))}

        x_igd_gms = self.__get_x_igd_gms()
        if x_igd_gms is not None:
            result["x-igd-gms"] = x_igd_gms

        return result

    def __get_legacy_rom_file_path(self, vm_meta_data: VmMetaData) -> Path:
        """Получить путь к legacy Video BIOS для режима Legacy

        :param vm_meta_data: Метаданные виртуальной машины
        :return: Путь к ROM-файлу
        :raises Exception: Если Video BIOS не найден или режим загрузки хоста неизвестен

        .. note::
           На хосте с BIOS Video BIOS можно выдернуть из sysfs пробрасываемого
           устройства, на хосте с UEFI его нужно извлечь из UEFI материнской
           платы (секция ``C5A4306E-E247-4ECD-A9D8-5B1985D3DCDA``)
        """
        rom_file_path = self.__get_legacy_video_bios_rom_path(vm_meta_data)
        if rom_file_path.exists():
            return rom_file_path

        if CurrentOs.is_bios_boot():
            # На хосте с BIOS legacy Video BIOS можно выдернуть из sysfs пробрасываемого устройства
            rom_file_path = self.get_rom(vm_meta_data.get_working_dir_path())
            if rom_file_path.exists():
                return rom_file_path
            raise Exception("[VgaPciIntel] Legacy passthrough: Video BIOS (legacy) NOT FOUND\n"
                            "Extract Video BIOS from motherboard BIOS by instruction and try again")

        if CurrentOs.is_uefi_boot():
            # На хосте с UEFI legacy Video BIOS извлекается из UEFI материнской платы
            raise Exception(
                "[VgaPciIntel] Legacy passthrough: Video BIOS (legacy) NOT FOUND\n"
                "Extract Video BIOS from motherboard UEFI (section C5A4306E-E247-4ECD-A9D8-5B1985D3DCDA) "
                "by instruction and try again")

        raise Exception("[VgaPciIntel] Legacy passthrough NOT SUPPORTED: unknown host boot mode")

    def __get_vfio_igd_pkg_options_table(self, vm_meta_data: VmMetaData) -> dict[str, typing.Any]:
        """Получить параметры устройства ``vfio-pci`` для режима VfioIgdPkg

        :param vm_meta_data: Метаданные виртуальной машины
        :return: Параметры устройства ``vfio-pci``
        :raises Exception: Если гость или хост не UEFI либо Video BIOS (EFI) не найден

        .. note::
           Требуется UEFI гость на UEFI хосте. Video BIOS (EFI) должен быть
           собран из исходников проекта VfioIgdPkg

        .. seealso::
           https://github.com/tomitamoeko/VfioIgdPkg
        """
        self.__check_uefi_passthrough_supported(VmMetaData.IgdPassthroughMode.VFIO_IGD_PKG, vm_meta_data)

        rom_file_no_video_path, rom_file_path, _intel_gop_driver_file_path = VfioIgdPkgRom(
            self.__get_base_path(vm_meta_data), self.get_id()).get_paths()
        if rom_file_path.exists():
            return self.__get_firmware_options_table(rom_file_path)
        if rom_file_no_video_path.exists():
            return self.__get_firmware_options_table(rom_file_no_video_path)
        raise Exception(
            "[VgaPciIntel] VfioIgdPkg: Video BIOS (EFI) NOT FOUND\nBuild Video BIOS by instruction and try again")

    def __get_i915ovmf_pkg_options_table(self, vm_meta_data: VmMetaData) -> dict[str, typing.Any]:
        """Получить параметры устройства ``vfio-pci`` для режима i915ovmfPkg

        :param vm_meta_data: Метаданные виртуальной машины
        :return: Параметры устройства ``vfio-pci``
        :raises Exception: Если гость или хост не UEFI либо Video BIOS (EFI) не найден

        .. note::
           Требуется UEFI гость на UEFI хосте. Video BIOS (EFI) должен быть
           собран из исходников проекта i915ovmfPkg

        .. seealso::
           https://github.com/x78x79x82x79/i915ovmfPkg
        """
        self.__check_uefi_passthrough_supported(VmMetaData.IgdPassthroughMode.I915OVMF_PKG, vm_meta_data)

        rom_file_path = i915ovmfRom(self.__get_base_path(vm_meta_data), self.get_id()).get_path()
        if not rom_file_path.exists():
            raise Exception(
                "[VgaPciIntel] i915ovmf: Video BIOS (EFI) NOT FOUND\nBuild Video BIOS by instruction and try again")
        return self.__get_firmware_options_table(rom_file_path)

    @staticmethod
    def __check_uefi_passthrough_supported(mode: VmMetaData.IgdPassthroughMode,
                                           vm_meta_data: VmMetaData) -> None:
        """Проверить, что гость и хост загружаются через UEFI

        :param mode: Режим проброса (для текста исключения)
        :param vm_meta_data: Метаданные виртуальной машины
        :raises Exception: Если гость или хост загружаются не через UEFI

        .. note::
           Режимы с готовым Video BIOS (EFI) работают только в комбинации
           UEFI гость + UEFI хост
        """
        platform = vm_meta_data.get_platform()
        if platform.is_uefi_boot() and CurrentOs.is_uefi_boot():
            return
        raise Exception(
            f"[VgaPciIntel] {mode.value} passthrough NOT SUPPORTED: UEFI guest and UEFI host required")

    @staticmethod
    def __get_firmware_options_table(rom_file_path: Path) -> dict[str, typing.Any]:
        """Получить общие параметры ``vfio-pci`` для режимов с Video BIOS (EFI)

        :param rom_file_path: Путь к Video BIOS (EFI)
        :return: Параметры устройства ``vfio-pci``

        .. note::
           ROM BAR включён (``rombar=1``), legacy VGA и OpRegion не используются.
           Устройство должно быть назначено на гостевой адрес ``00:02.0``
        """
        return {"addr": "0x02",
                "rombar": 1,
                "x-igd-legacy-mode": "off",
                "x-vga": "off",
                "x-igd-opregion": "off",
                "x-igd-lpc": "off",
                "romfile": str(rom_file_path)}

    @staticmethod
    def __get_base_path(vm_meta_data: VmMetaData) -> BasePath:
        """Получить базовый путь для файлов ROM, специфичных для платформы

        :param vm_meta_data: Метаданные виртуальной машины
        :return: Базовый путь с архитектурой гостя
        """
        return BasePath(vm_meta_data.get_platform().get_arch())
