import os
import re

from lib.python.system import CurrentOs

from lib.python.shell import RunScriptInShellDecorator
from lib.python.shell import UNIX_SHELL_SCRIPT_FILE_EXTENSION_DEFAULT, WIN_SHELL_SCRIPT_FILE_EXTENSION_DEFAULT


class Shell:
    @staticmethod
    def get_possible_extensions_regex():
        return "|".join(map(re.escape, WIN_SHELL_SCRIPT_FILE_EXTENSION_DEFAULT + UNIX_SHELL_SCRIPT_FILE_EXTENSION_DEFAULT))

    def __init__(self, is_windows: bool = CurrentOs.is_windows()):
        self.__is_windows = is_windows

    def suppress_stdout_stderr(self, is_suppress_stdout: bool = True, is_suppress_stderr: bool = True) -> str:
        if is_suppress_stdout and is_suppress_stderr:
            return f"{self.suppress_stdout()} 2>&1"
        elif is_suppress_stdout:
            return self.suppress_stdout()
        elif is_suppress_stderr:
            return self.suppress_stderr()
        return ""

    def suppress_stdout(self) -> str:
        if self.__is_windows:
            # https://www.robvanderwoude.com/redirection.php
            return '>NUL'
        else:
            return '> "/dev/null"'

    def suppress_stderr(self) -> str:
        return f"2{self.suppress_stdout()}"

    def get_script_file_extension(self) -> str:
        if self.__is_windows:
            return WIN_SHELL_SCRIPT_FILE_EXTENSION_DEFAULT
        else:
            return UNIX_SHELL_SCRIPT_FILE_EXTENSION_DEFAULT

    def get_run_script_in_shell_command_line(self, shell_script_path: str | os.PathLike[str]) -> str:
        @RunScriptInShellDecorator(shell_script_path)
        def __get_run_script_in_shell_command_line() -> str:
            return str(shell_script_path)

        return __get_run_script_in_shell_command_line()

    def make_script(self, script_body, is_debug=False):
        if self.__is_windows:
            utf8_encoding = 65001
            return f'cpch {utf8_encoding}\n{"@echo off\n" if bool(is_debug) else ""}\n{script_body}\n'
        else:
            return f'#!/bin/bash\n{"set -x\n" if bool(is_debug) else ""}\n{script_body}\n'