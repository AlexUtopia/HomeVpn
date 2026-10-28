"""Управление питанием: перезагрузка и выключение"""

import subprocess
import time

from lib.python.logger.logger import Logger
from lib.python.system.current_os import CurrentOs

from lib.python.shell.run_in_cmd_shell_decorator import RunInCmdShellDecorator


class Power:
    """Управление питанием

    .. note::
       Windows, MSYS2 и Cygwin поддерживаются через cmd.exe
    .. seealso::
       https://pythonassets.com/posts/shutdown-reboot-and-log-off-on-windows-and-linux/
    """

    @staticmethod
    def reboot() -> None:
        """Перезагрузить систему

        :raises RuntimeError: Если платформа не поддерживается
        """
        if CurrentOs.is_linux():
            Logger.instance().warning("[Power] reboot!!!")
            Power.__reboot_linux()
            Power.__wait_of_poweroff()
        elif CurrentOs.is_windows_platform():
            Logger.instance().warning("[Power] reboot!!!")
            Power.__reboot_windows()
            Power.__wait_of_poweroff()
        else:
            raise RuntimeError("[Power] reboot not supported")

    @staticmethod
    def poweroff() -> None:
        """Выключить систему

        :raises RuntimeError: Если платформа не поддерживается
        """
        if CurrentOs.is_linux():
            Logger.instance().warning("[Power] poweroff!!!")
            Power.__poweroff_linux()
            Power.__wait_of_poweroff()
        elif CurrentOs.is_windows_platform():
            Logger.instance().warning("[Power] poweroff!!!")
            Power.__poweroff_windows()
            Power.__wait_of_poweroff()
        else:
            raise RuntimeError("[Power] poweroff not supported")

    @staticmethod
    def __reboot_linux() -> None:
        """Перезагрузить систему на Linux"""
        subprocess.check_call(["reboot"], shell=True)

    @staticmethod
    def __poweroff_linux() -> None:
        """Выключить систему на Linux"""
        subprocess.check_call(["poweroff"], shell=True)

    @staticmethod
    def __reboot_windows() -> None:
        """Перезагрузить систему на Windows, MSYS2 и Cygwin"""

        @RunInCmdShellDecorator()
        def __get_reboot_command() -> str:
            return "shutdown /r /t 0"

        subprocess.check_call(__get_reboot_command(), shell=True)

    @staticmethod
    def __poweroff_windows() -> None:
        """Выключить систему на Windows, MSYS2 и Cygwin"""

        @RunInCmdShellDecorator()
        def __get_poweroff_command() -> str:
            return "shutdown /s /t 0"

        subprocess.check_call(__get_poweroff_command(), shell=True)

    @staticmethod
    def __wait_of_poweroff() -> None:
        """Ожидать выключения системы"""
        while True:
            time.sleep(60)
