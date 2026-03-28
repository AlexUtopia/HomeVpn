import cpuinfo
import os_release
import pathlib
import platform
import semantic_version
import subprocess
import sys

from lib.python.types import LinuxKernelVersion


# https://tproger.ru/translations/demystifying-decorators-in-python/

# https://devblogs.microsoft.com/oldnewthing/20050201-00/?p=36553
# https://stackoverflow.com/a/43512141
# https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-osversioninfoexa#remarks
# https://stackoverflow.com/a/54837707
class CurrentOs:

    ## Проверить что текущая ОС и её архитектура являются целевыми
    # @details Архитектура может не указываться
    # @details Правильные примеры:
    #              linux:x86_64
    #              win:amd64
    #              Android/termux:aarch64
    #              Android/termux:armv8l
    #          Неправильные примеры:
    #              linux:arm - "arm" библиотека cpuinfo не принимает
    # @param [in] os_and_arch_for_check Целевая ОС и её архитектура
    # @return True - текущая ОС является целевой; False - нет
    @staticmethod
    def check_os_and_arch(os_and_arch_for_check: str) -> bool:
        maxsplit = 2
        os_vs_arch = os_and_arch_for_check.split(":", maxsplit=maxsplit)
        os_for_check = os_vs_arch[0]
        result = CurrentOs.check_os(os_for_check)
        if len(os_vs_arch) == maxsplit:
            arch_for_check = os_vs_arch[1]
            return result and CurrentOs.check_arch(arch_for_check)
        return result

    ## Проверить что текущая ОС является целевой
    # @details Проверка на Android/termux должна идти перед проверкой на Linux,
    #          т.к. иначе может случиться ложноположительная проверка на Linux
    #          (хотя безусловно Android/termux это своего рода Linux)
    # @param [in] os_for_check Целевая ОС
    # @return True - текущая ОС является целевой; False - нет
    @staticmethod
    def check_os(os_for_check: str) -> bool:
        return (CurrentOs.is_termux(os_for_check) and CurrentOs.is_termux()) or (
                CurrentOs.is_linux(os_for_check) and CurrentOs.is_linux()) or (
                CurrentOs.is_windows(os_for_check) and CurrentOs.is_windows()) or (
                CurrentOs.is_msys(os_for_check) and CurrentOs.is_msys()) or (
                CurrentOs.is_cygwin(os_for_check) and CurrentOs.is_cygwin())

    ## Проверить что текущая архитектура ОС является целевой
    # @details Допустимые значения arch_for_check можно увидеть здесь
    #          https://github.com/workhorsy/py-cpuinfo/blob/master/cpuinfo/cpuinfo.py#L782
    # @details Полезные ссылки на тему
    #          https://unix.stackexchange.com/questions/136959/where-does-uname-get-its-information-from
    #          https://habr.com/ru/companies/intel/articles/201462/
    #          https://stackoverflow.com/questions/45125516/possible-values-for-uname-m
    #          https://github.com/torvalds/linux/blob/master/scripts/package/mkdebian#L21
    #          http://ports.ubuntu.com/ubuntu-ports/dists/noble/main/
    #          http://archive.ubuntu.com/ubuntu/dists/noble/main/
    #          https://youtu.be/6DybX5Lkqt4?si=jocEAhC03jxshFLQ
    # @details В настоящий момент сделано по-простому - с использованием библиотеки cpuinfo
    # @param [in] os_for_check Целевая архитектура ОС
    # @return True - текущая архитектура ОС является целевой; False - нет
    @staticmethod
    def check_arch(arch_for_check: str) -> bool:
        my_cpu_info = cpuinfo.get_cpu_info()
        my_arch: str = my_cpu_info["arch"]
        my_bits: int = my_cpu_info["bits"]
        return cpuinfo.cpuinfo._parse_arch(arch_for_check) == (my_arch, my_bits)

    @staticmethod
    def is_windows_platform() -> bool:
        return CurrentOs.is_windows() or CurrentOs.is_msys() or CurrentOs.is_cygwin()

    @staticmethod
    def is_windows(my_platform: str = sys.platform) -> bool:
        # https://docs.python.org/3/library/sys.html#sys.platform
        return my_platform.lower().startswith('win')

    @staticmethod
    def is_msys(my_platform: str = sys.platform) -> bool:
        # https://docs.python.org/3/library/sys.html#sys.platform
        return my_platform.lower().startswith('msys')

    @staticmethod
    def is_cygwin(my_platform: str = sys.platform) -> bool:
        # https://docs.python.org/3/library/sys.html#sys.platform
        return my_platform.lower().startswith('cygwin')

    @staticmethod
    def is_linux(my_platform: str = sys.platform) -> bool:
        # https://docs.python.org/3/library/sys.html#sys.platform
        return my_platform.lower().startswith('linux')

    @staticmethod
    def is_termux(my_platform: str = sys.platform) -> bool:
        if my_platform and isinstance(my_platform, str):
            return 'termux' in my_platform.lower()
        # https://termux.dev/en/
        return CurrentOs.is_android(my_platform)

    # В python 3.13 sys.platform == "android" а не "linux"
    # https://docs.python.org/3/library/sys.html#sys.platform
    @staticmethod
    def is_android(my_platform: str = sys.platform) -> bool:
        if my_platform and isinstance(my_platform, str):
            return 'android' in my_platform.lower()

        try:
            cmd_result = subprocess.run("uname -o", shell=True, capture_output=True, text=True)
            if cmd_result.returncode:
                return False
            return cmd_result.stdout.lower().startswith("android")
        except Exception:
            return False

    @staticmethod
    def get_linux_kernel_version() -> LinuxKernelVersion | None:
        if not CurrentOs.is_linux():
            return None
        # https://docs.python.org/3/library/os.html#os.uname
        return LinuxKernelVersion(platform.release())

    @staticmethod
    def get_windows_version() -> semantic_version.Version | None:
        if not CurrentOs.is_windows():
            return None
        os_version_info_ex = sys.getwindowsversion()
        # fixme utopia Добавить информацию про wProductType
        return semantic_version.Version(major=os_version_info_ex.major, minor=os_version_info_ex.minor,
                                        build=os_version_info_ex.build)

    @staticmethod
    def is_ubuntu_or_like() -> bool:
        return CurrentOs.__is_linux_distro_or_like("ubuntu")

    @staticmethod
    def is_debian_or_like() -> bool:
        return CurrentOs.__is_linux_distro_or_like("debian")

    @staticmethod
    def is_arch_or_like() -> bool:
        return CurrentOs.__is_linux_distro_or_like("arch")

    @staticmethod
    def __is_linux_distro_or_like(linux_distro_id: str) -> bool:
        try:
            if not CurrentOs.is_linux():
                return False

            linux_distro_id = linux_distro_id.strip().lower()
            current_linux_distro_info = os_release.current_release()
            return (linux_distro_id == current_linux_distro_info.id) or (
                    linux_distro_id in current_linux_distro_info.id_like)
        except Exception:
            return False

    @staticmethod
    def get_linux_distro_name() -> str | None:
        if not CurrentOs.is_linux():
            return None
        # https://pypi.org/project/os-release/
        # https://www.freedesktop.org/software/systemd/man/os-release.html
        return os_release.current_release().id

    @staticmethod
    def get_linux_distro_version() -> semantic_version.Version | None:
        if not CurrentOs.is_linux():
            return None
        # https://pypi.org/project/os-release/
        # https://www.freedesktop.org/software/systemd/man/os-release.html
        return semantic_version.Version(version_string=os_release.current_release().version_id)

    # fixme utopia Проверить на Ubuntu 32bit
    # https://askubuntu.com/questions/768415/where-can-i-find-32-bit-version-of-ubuntu
    @staticmethod
    def is32bit() -> bool:
        return platform.architecture()[0].lower() == "32bit"

    @staticmethod
    def is64bit() -> bool:
        # https://www.fastwebhost.in/blog/how-to-find-if-linux-is-running-on-32-bit-or-64-bit/
        # https://wiki.termux.com/wiki/FAQ
        return platform.architecture()[0].lower() == "64bit"

    # https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/boot-to-uefi-mode-or-legacy-bios-mode?view=windows-11
    # https://www.hindicodingcommunity.com/2023/02/how-to-check-whether-secure-boot-is.html
    # https://www.ninjaone.com/blog/confirm-if-secure-boot-is-enabled-or-disabled/
    # https://www.tenforums.com/tutorials/85195-check-if-windows-10-using-uefi-legacy-bios.html
    # https://stackoverflow.com/questions/65314573/how-to-check-device-boot-mode-uefi-or-legacy
    # https://stackoverflow.com/questions/18172197/programmatically-determine-if-windows-8-secure-boot-is-enabled
    # https://learn.microsoft.com/en-us/powershell/module/secureboot/?view=windowsserver2025-ps
    @staticmethod
    def is_bios_boot() -> bool:
        if CurrentOs.is_linux():
            return not pathlib.Path("/sys/firmware/efi").exists()
        elif CurrentOs.is_windows():
            return False
        return False

    @staticmethod
    def is_uefi_boot() -> bool:
        if CurrentOs.is_linux():
            return pathlib.Path("/sys/firmware/efi").exists()
        elif CurrentOs.is_windows():
            return False
        return False

    # https://wiki.debian.org/SecureBoot#What_is_UEFI_Secure_Boot.3F
    # https://wiki.archlinux.org/title/Unified_Extensible_Firmware_Interface/Secure_Boot#Checking_Secure_Boot_status
    @staticmethod
    def is_uefi_secure_boot(self) -> bool:
        return CurrentOs.is_uefi_boot() and False
