"""Декоратор запуска команды в cmd.exe с учётом особенностей платформы"""

import typing

from lib.python.system.current_os import CurrentOs

from .shell_bash_decorator import ShellBashDecorator
from .shell_bash_script_decorator import ShellBashScriptDecorator
from .shell_cmd_decorator import ShellCmdDecorator
from .shell_wine_decorator import ShellWineDecorator
from .shell_decorator_type import ShellCommand, ShellDecorator


class RunInCmdShellDecorator:
    """Оборачивает команду в запуск cmd.exe с учётом особенностей платформы

    .. note::
       На Unix-подобных системах cmd.exe запускается через wine
    """

    def __init__(self, shell_cmd_decorator: ShellDecorator = ShellCmdDecorator(),
                 shell_bash_decorator: ShellDecorator = ShellBashDecorator(),
                 shell_wine_decorator: ShellDecorator = ShellWineDecorator()) -> None:
        """Инициализировать декоратор

        :param shell_cmd_decorator: Декоратор запуска в cmd.exe
        :param shell_bash_decorator: Декоратор запуска в bash
        :param shell_wine_decorator: Декоратор запуска через wine
        """
        self.__shell_cmd_decorator = shell_cmd_decorator
        self.__shell_bash_decorator = shell_bash_decorator
        self.__shell_wine_decorator = shell_wine_decorator

    def __call__(self, func: ShellCommand) -> ShellCommand:
        """Обернуть функцию, возвращающую команду, в запуск cmd.exe

        :param func: Функция, возвращающая команду
        :return: Обёрнутая функция
        """

        @self.__shell_cmd_decorator
        def __decorator_func_cmd(*args: typing.Any, **kwargs: typing.Any) -> str:
            return func(*args, **kwargs)

        @self.__shell_bash_decorator
        @self.__shell_cmd_decorator
        def __decorator_func_win_unix(*args: typing.Any, **kwargs: typing.Any) -> str:
            return func(*args, **kwargs)

        @self.__shell_bash_decorator
        @ShellBashScriptDecorator([self.__shell_wine_decorator, self.__shell_cmd_decorator], ".cmd")
        def __decorator_func_unix(*args: typing.Any, **kwargs: typing.Any) -> str:
            return func(*args, **kwargs)

        if CurrentOs.is_windows():
            return __decorator_func_cmd
        if CurrentOs.is_msys() or CurrentOs.is_cygwin():
            return __decorator_func_win_unix
        return __decorator_func_unix
