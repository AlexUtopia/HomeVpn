"""Декоратор запуска команды в bash с учётом особенностей Windows"""

import typing

from lib.python.system.current_os import CurrentOs

from .shell_bash_decorator import ShellBashDecorator
from .shell_cmd_decorator import ShellCmdDecorator
from .shell_msys2_decorator import ShellMsys2Decorator
from .shell_decorator_type import ShellCommand, ShellDecorator


class RunInBashShellDecorator:
    """Оборачивает команду в запуск bash с учётом особенностей Windows

    .. note::
       На Windows bash может быть доступен только внутри MSYS2 или Cygwin
    """

    WIN_BASH_INTERNAL_CALL = 0
    WIN_BASH_EXTERNAL_CALL = 1
    WIN_BASH_MSYS2 = 2
    WIN_BASH_CYGWIN = 3

    def __init__(self, win_bash: int = WIN_BASH_INTERNAL_CALL,
                 shell_bash_decorator: ShellDecorator = ShellBashDecorator(),
                 shell_cmd_decorator: ShellDecorator = ShellCmdDecorator(),
                 shell_msys2_decorator: ShellDecorator = ShellMsys2Decorator()) -> None:
        """Инициализировать декоратор

        :param win_bash: Способ вызова bash на Windows
        :param shell_bash_decorator: Декоратор запуска в bash
        :param shell_cmd_decorator: Декоратор запуска в cmd.exe
        :param shell_msys2_decorator: Декоратор запуска в MSYS2 shell
        """
        self.__win_bash = win_bash
        self.__shell_bash_decorator = shell_bash_decorator
        self.__shell_cmd_decorator = shell_cmd_decorator
        self.__shell_msys2_decorator = shell_msys2_decorator

    def __call__(self, func: ShellCommand) -> ShellCommand:
        """Обернуть функцию, возвращающую команду, в запуск bash

        :param func: Функция, возвращающая команду
        :return: Обёрнутая функция

        .. note::
           На Windows без MSYS2/Cygwin выбрасывается исключение
        :raises RuntimeError: Если bash на Windows недоступен
        """

        @self.__shell_bash_decorator
        def __decorator_func_bash(*args: typing.Any, **kwargs: typing.Any) -> str:
            return func(*args, **kwargs)

        @self.__shell_cmd_decorator
        @self.__shell_msys2_decorator
        def __decorator_func_msys2(*args: typing.Any, **kwargs: typing.Any) -> str:
            return __decorator_func_bash(*args, **kwargs)

        @self.__shell_cmd_decorator
        def __decorator_func_cygwin(*args: typing.Any, **kwargs: typing.Any) -> str:
            return __decorator_func_bash(*args, **kwargs)

        if not CurrentOs.is_windows_platform():
            return __decorator_func_bash

        if self.__win_bash == self.WIN_BASH_INTERNAL_CALL:
            if CurrentOs.is_msys() or CurrentOs.is_cygwin():
                return __decorator_func_bash
            raise RuntimeError("[bash] Windows bash NOT AVAILABLE")

        if self.__win_bash == self.WIN_BASH_EXTERNAL_CALL:
            if CurrentOs.is_msys():
                return __decorator_func_msys2
            if CurrentOs.is_cygwin():
                return __decorator_func_cygwin
            raise RuntimeError("[bash] Windows bash NOT AVAILABLE")

        if self.__win_bash == self.WIN_BASH_MSYS2:
            return __decorator_func_msys2
        if self.__win_bash == self.WIN_BASH_CYGWIN:
            return __decorator_func_cygwin

        raise RuntimeError("[bash] Windows bash NOT SUPPORTED")
