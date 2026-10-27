"""Запуск исполняемых скриптов проекта в подходящей оболочке"""

import os
import pathlib

from lib.python.types.path import Path

from lib.python.shell.run_in_bash_shell_decorator import RunInBashShellDecorator
from lib.python.shell.run_script_in_shell_decorator import RunScriptInShellDecorator


class ProjectScript:
    """Исполняемый скрипт проекта

    .. note::
       Для запуска используется оболочка, соответствующая расширению скрипта
    """

    CONFIG_PROJECT_INSTANCE_FILE_PATH = "CONFIG_PROJECT_INSTANCE_FILE_PATH"

    def __init__(self, script_file_path: str | os.PathLike[str] = "run_cmd.sh",
                 win_bash: int = RunInBashShellDecorator.WIN_BASH_EXTERNAL_CALL) -> None:
        """Инициализировать исполняемый скрипт проекта

        :param script_file_path: Путь до исполняемого скрипта
        :param win_bash: Способ вызова bash на Windows
        """
        self.__script_file_path = Path(script_file_path)
        self.__win_bash = win_bash

    def get_run_cmd_in_shell(self, args: str) -> str:
        """Получить командную строку запуска скрипта в подходящей оболочке

        :param args: Аргументы командной строки
        :return: Командная строка запуска скрипта
        """

        @RunScriptInShellDecorator(shell_script_path=self.__script_file_path,
                                   run_in_bash_shell_decorator=RunInBashShellDecorator(
                                       win_bash=self.__win_bash))
        def __get_run_cmd_in_shell() -> str:
            return self.get_run_cmd(args)

        return __get_run_cmd_in_shell()

    def get_run_cmd(self, args: str) -> str:
        """Получить командную строку запуска скрипта

        :param args: Аргументы командной строки
        :return: Командная строка запуска скрипта
        """
        instance_config_path = self.__get_current_project_instance_config_path()
        return (f'{self.CONFIG_PROJECT_INSTANCE_FILE_PATH}="{instance_config_path}"'
                f' "{self.__script_file_path}" {args}')

    def __get_current_project_instance_config_path(self) -> pathlib.Path:
        """Получить путь до конфигурации текущего экземпляра проекта

        :return: Путь до файла конфигурации
        """
        return pathlib.Path(os.environ[self.CONFIG_PROJECT_INSTANCE_FILE_PATH])
