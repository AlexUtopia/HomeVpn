import os
import pathlib

from lib.python.types import Path

from lib.python.shell import RunScriptInShellDecorator
from lib.python.shell import RunInBashShellDecorator


class ProjectScript:
    CONFIG_PROJECT_INSTANCE_FILE_PATH = "CONFIG_PROJECT_INSTANCE_FILE_PATH"

    def __init__(self, script_file_path="run_cmd.sh", win_bash: int = RunInBashShellDecorator.WIN_BASH_AUTO_SELECT):
        self.__script_file_path = Path(script_file_path)
        self.__win_bash = win_bash

    def get_run_cmd_in_shell(self, args) -> str:
        @RunScriptInShellDecorator(shell_script_path=self.__script_file_path,
                                   run_in_bash_shell_decorator=RunInBashShellDecorator(
                                       win_bash=self.__win_bash))
        def __get_run_cmd_in_shell() -> str:
            return self.get_run_cmd(args)

        return __get_run_cmd_in_shell()

    def get_run_cmd(self, args: str) -> str:
        return f'{self.CONFIG_PROJECT_INSTANCE_FILE_PATH}="{self.__get_current_project_instance_config_path()}" "{self.__script_file_path}" {args}'

    def __get_current_project_instance_config_path(self) -> pathlib.Path:
        return pathlib.Path(os.environ[self.CONFIG_PROJECT_INSTANCE_FILE_PATH])
