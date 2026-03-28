import os
import pathlib

from run_in_bash_shell_decorator import RunInBashShellDecorator
from run_in_cmd_shell_decorator import RunInCmdShellDecorator


class RunScriptInShellDecorator:
    WIN_SHELL_SCRIPT_FILE_EXTENSION_LIST = {".cmd", ".bat", ".com"}
    UNIX_SHELL_SCRIPT_FILE_EXTENSION_LIST = {".sh", ".bash"}

    def __init__(self, shell_script_path: str | os.PathLike[str], run_in_cmd_shell_decorator=RunInCmdShellDecorator(),
                 run_in_bash_shell_decorator=RunInBashShellDecorator()):
        self.__shell_script_path = pathlib.Path(shell_script_path)
        self.__run_in_cmd_shell_decorator = run_in_cmd_shell_decorator
        self.__run_in_bash_shell_decorator = run_in_bash_shell_decorator

    def __call__(self, func):
        @self.__run_in_cmd_shell_decorator
        def __decorator_func_run_in_cmd_shell(*args, **kwargs):
            return func(*args, **kwargs)

        @self.__run_in_bash_shell_decorator
        def __decorator_func_run_in_bash_shell(*args, **kwargs):
            return func(*args, **kwargs)

        shell_script_extension = self.__shell_script_path.suffix
        if shell_script_extension in self.WIN_SHELL_SCRIPT_FILE_EXTENSION_LIST:
            return __decorator_func_run_in_cmd_shell
        elif shell_script_extension in self.UNIX_SHELL_SCRIPT_FILE_EXTENSION_LIST:
            return __decorator_func_run_in_bash_shell
        else:
            return func
