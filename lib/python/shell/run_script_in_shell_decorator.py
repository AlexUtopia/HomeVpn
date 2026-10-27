"""Декоратор запуска shell-скрипта в подходящей для него оболочке"""

import os
import pathlib
import typing

from .run_in_bash_shell_decorator import RunInBashShellDecorator
from .run_in_cmd_shell_decorator import RunInCmdShellDecorator
from .shell_script_extension import UNIX_SHELL_SCRIPT_FILE_EXTENSION_LIST, WIN_SHELL_SCRIPT_FILE_EXTENSION_LIST
from .shell_decorator_type import ShellCommand, ShellDecorator


class RunScriptInShellDecorator:
    """Оборачивает запуск shell-скрипта в подходящую оболочку

    .. note::
       Оболочка выбирается по расширению файла скрипта
    """

    def __init__(self, shell_script_path: str | os.PathLike[str],
                 run_in_cmd_shell_decorator: ShellDecorator = RunInCmdShellDecorator(),
                 run_in_bash_shell_decorator: ShellDecorator = RunInBashShellDecorator()) -> None:
        """Инициализировать декоратор

        :param shell_script_path: Путь до shell-скрипта
        :param run_in_cmd_shell_decorator: Декоратор запуска в cmd.exe
        :param run_in_bash_shell_decorator: Декоратор запуска в bash
        """
        self.__shell_script_path = pathlib.Path(shell_script_path)
        self.__run_in_cmd_shell_decorator = run_in_cmd_shell_decorator
        self.__run_in_bash_shell_decorator = run_in_bash_shell_decorator

    def __call__(self, func: ShellCommand) -> ShellCommand:
        """Обернуть функцию, возвращающую команду, в запуск shell-скрипта

        :param func: Функция, возвращающая команду
        :return: Обёрнутая функция
        """

        @self.__run_in_cmd_shell_decorator
        def __decorator_func_run_in_cmd_shell(*args: typing.Any, **kwargs: typing.Any) -> str:
            return func(*args, **kwargs)

        @self.__run_in_bash_shell_decorator
        def __decorator_func_run_in_bash_shell(*args: typing.Any, **kwargs: typing.Any) -> str:
            return func(*args, **kwargs)

        shell_script_extension = self.__shell_script_path.suffix
        if shell_script_extension in WIN_SHELL_SCRIPT_FILE_EXTENSION_LIST:
            return __decorator_func_run_in_cmd_shell
        if shell_script_extension in UNIX_SHELL_SCRIPT_FILE_EXTENSION_LIST:
            return __decorator_func_run_in_bash_shell
        return func
