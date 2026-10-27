"""Декоратор запуска команды в MSYS2 shell"""

import os
import pathlib
import subprocess
import typing

from lib.python.logger.logger import Logger
from lib.python.system.arch import Arch
from lib.python.system.current_os import CurrentOs

from .shell_bash_decorator import ShellBashDecorator
from .shell_cmd_decorator import ShellCmdDecorator


class ShellMsys2Decorator:
    """Оборачивает команду в вызов msys2_shell.cmd

    .. note::
       Используется для запуска MSYS2 shell через wine или docker
    .. seealso::
       https://github.com/msys2/msys2-docker/pkgs/container/msys2-docker-experimental
       https://github.com/msys2/MSYS2-packages/blob/master/filesystem/msys2_shell.cmd
    """

    @staticmethod
    def get_msys2_shell() -> pathlib.Path:
        """Получить путь до msys2_shell.cmd

        :return: Путь до msys2_shell.cmd

        .. note::
           Если определить путь через ``cygpath`` не удалось, используется путь по умолчанию
        """
        if CurrentOs.is_msys():
            call_result = subprocess.run("cygpath -m /", shell=True, capture_output=True, text=True, check=False)
            if not call_result.returncode:
                return pathlib.Path(call_result.stdout) / "msys64" / "msys2_shell.cmd"
            Logger.instance().warning("[msys2] Get msys2_shell.cmd path from cygpath FAIL, use default")
        return pathlib.Path(r"%SYSTEMDRIVE%\msys64\msys2_shell.cmd")

    @staticmethod
    def get_msys2_environment() -> str:
        """Получить имя окружения MSYS2 для текущей архитектуры

        :return: Имя окружения MSYS2
        :raises RuntimeError: Если архитектура не поддерживается
        """
        if CurrentOs.is_msys():
            return os.environ["MSYSTEM"].lower()

        if Arch() == Arch("x86_64"):
            return "clang64"
        if Arch() == Arch("aarch64"):
            return "clangarm64"
        raise RuntimeError("[msys2] Platform NOT SUPPORT")

    def __init__(self, msys2_shell_script_path: str | os.PathLike[str] = get_msys2_shell(),
                 msys2_environment: str = get_msys2_environment()) -> None:
        """Инициализировать декоратор

        :param msys2_shell_script_path: Путь до msys2_shell.cmd
        :param msys2_environment: Имя окружения MSYS2
        """
        self.__msys2_shell_script_path = pathlib.Path(msys2_shell_script_path)
        self.__msys2_environment = msys2_environment

    def __call__(self, func: typing.Callable[..., str]) -> typing.Callable[..., str]:
        """Обернуть функцию, возвращающую команду, в вызов msys2_shell.cmd

        :param func: Функция, возвращающая команду
        :return: Обёрнутая функция
        """

        def __decorator_func(*args: typing.Any, **kwargs: typing.Any) -> str:
            cmd_line = func(*args, **kwargs)
            cmd_line = ShellBashDecorator().escape_cmd_line_for_win(cmd_line)
            cmd_line = ShellCmdDecorator().full_escape_cmd_line(cmd_line)
            return f'"{self.__msys2_shell_script_path}" -no-start -{self.__msys2_environment}' \
                   f' -defterm -c "{cmd_line}"'

        return __decorator_func
