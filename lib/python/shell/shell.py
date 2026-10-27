"""Утилиты обёртки команд в командную оболочку текущей ОС"""

import os
import re

from lib.python.system.current_os import CurrentOs

from .run_script_in_shell_decorator import RunScriptInShellDecorator
from .shell_script_extension import UNIX_SHELL_SCRIPT_FILE_EXTENSION_DEFAULT, WIN_SHELL_SCRIPT_FILE_EXTENSION_DEFAULT


class Shell:
    """Командная оболочка текущей ОС"""

    @staticmethod
    def get_possible_extensions_regex() -> str:
        """Получить регулярное выражение возможных расширений shell-скриптов

        :return: Регулярное выражение расширений
        """
        extensions = WIN_SHELL_SCRIPT_FILE_EXTENSION_DEFAULT + UNIX_SHELL_SCRIPT_FILE_EXTENSION_DEFAULT
        return "|".join(map(re.escape, extensions))

    def __init__(self, is_windows: bool = CurrentOs.is_windows()) -> None:
        """Инициализировать обёртку командной оболочки

        :param is_windows: Использовать синтаксис Windows
        """
        self.__is_windows = is_windows

    def suppress_stdout_stderr(self, is_suppress_stdout: bool = True, is_suppress_stderr: bool = True) -> str:
        """Получить перенаправление вывода в никуда

        :param is_suppress_stdout: Подавить stdout
        :param is_suppress_stderr: Подавить stderr
        :return: Фрагмент командной строки для перенаправления вывода
        """
        if is_suppress_stdout and is_suppress_stderr:
            return f"{self.suppress_stdout()} 2>&1"
        if is_suppress_stdout:
            return self.suppress_stdout()
        if is_suppress_stderr:
            return self.suppress_stderr()
        return ""

    def suppress_stdout(self) -> str:
        """Получить перенаправление stdout в никуда

        :return: Фрагмент командной строки для перенаправления stdout
        """
        if self.__is_windows:
            # https://www.robvanderwoude.com/redirection.php
            return '>NUL'
        return '> "/dev/null"'

    def suppress_stderr(self) -> str:
        """Получить перенаправление stderr в никуда

        :return: Фрагмент командной строки для перенаправления stderr
        """
        return f"2{self.suppress_stdout()}"

    def get_script_file_extension(self) -> str:
        """Получить расширение файла shell-скрипта

        :return: Расширение файла shell-скрипта
        """
        if self.__is_windows:
            return WIN_SHELL_SCRIPT_FILE_EXTENSION_DEFAULT
        return UNIX_SHELL_SCRIPT_FILE_EXTENSION_DEFAULT

    def get_run_script_in_shell_command_line(self, shell_script_path: str | os.PathLike[str]) -> str:
        """Получить командную строку запуска shell-скрипта

        :param shell_script_path: Путь до shell-скрипта
        :return: Командная строка запуска shell-скрипта
        """

        @RunScriptInShellDecorator(shell_script_path)
        def __get_run_script_in_shell_command_line() -> str:
            return str(shell_script_path)

        return __get_run_script_in_shell_command_line()

    def make_script(self, script_body: str, is_debug: bool = False) -> str:
        """Сформировать содержимое shell-скрипта

        :param script_body: Тело скрипта
        :param is_debug: Включить отладочный режим
        :return: Содержимое shell-скрипта
        """
        if self.__is_windows:
            utf8_encoding = 65001
            debug_prefix = "@echo off\n" if is_debug else ""
            return f'cpch {utf8_encoding}\n{debug_prefix}\n{script_body}\n'

        debug_prefix = "set -x\n" if is_debug else ""
        return f'#!/bin/bash\n{debug_prefix}\n{script_body}\n'
