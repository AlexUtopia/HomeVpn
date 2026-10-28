"""Декоратор запуска команды в cmd.exe с учётом особенностей платформы"""

import typing

from lib.python.system.current_os import CurrentOs

from .shell_bash_decorator import ShellBashDecorator
from .shell_bash_script_decorator import ShellBashScriptDecorator
from .shell_cmd_decorator import ShellCmdDecorator
from .shell_decorator_type import ShellCommand, ShellDecorator
from .shell_wine_decorator import ShellWineDecorator


class RunInCmdShellDecorator:
    """Оборачивает команду в запуск cmd.exe с учётом особенностей платформы

    .. note::
       Windows использует ``%COMSPEC%``, MSYS2/Cygwin — путь, полученный через ``cygpath``,
       на Unix-подобных системах cmd.exe запускается через wine
    """

    def __init__(self, shell_bash_decorator: ShellDecorator = ShellBashDecorator(),
                 shell_wine_decorator: ShellDecorator | None = None) -> None:
        """Инициализировать декоратор

        :param shell_bash_decorator: Декоратор запуска в bash
        :param shell_wine_decorator: Декоратор запуска через wine; если не задан, создаётся при необходимости
        """
        self.__shell_bash_decorator = shell_bash_decorator
        self.__shell_wine_decorator = shell_wine_decorator

    def __call__(self, func: ShellCommand) -> ShellCommand:
        """Обернуть функцию, возвращающую команду, в запуск cmd.exe

        :param func: Функция, возвращающая команду
        :return: Обёрнутая функция
        """
        if CurrentOs.is_windows():

            @ShellCmdDecorator()
            def __decorator_func_cmd(*args: typing.Any, **kwargs: typing.Any) -> str:
                return func(*args, **kwargs)

            return __decorator_func_cmd

        if CurrentOs.is_msys() or CurrentOs.is_cygwin():

            @self.__shell_bash_decorator
            @ShellCmdDecorator(cmd_path=r'$(cygpath -u "${COMSPEC}")')
            def __decorator_func_win_unix(*args: typing.Any, **kwargs: typing.Any) -> str:
                return func(*args, **kwargs)

            return __decorator_func_win_unix

        shell_wine_decorator = self.__shell_wine_decorator if self.__shell_wine_decorator else ShellWineDecorator()

        @self.__shell_bash_decorator
        @ShellBashScriptDecorator([shell_wine_decorator, ShellCmdDecorator()], ".cmd")
        def __decorator_func_unix(*args: typing.Any, **kwargs: typing.Any) -> str:
            return func(*args, **kwargs)

        return __decorator_func_unix
