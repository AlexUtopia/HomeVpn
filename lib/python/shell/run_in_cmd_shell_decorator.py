from lib.python.system import CurrentOs

from shell_bash_decorator import ShellBashDecorator
from shell_bash_script_decorator import ShellBashScriptDecorator
from shell_cmd_decorator import ShellCmdDecorator
from shell_wine_decorator import ShellWineDecorator


class RunInCmdShellDecorator:
    def __init__(self, shell_cmd_decorator=ShellCmdDecorator(), shell_bash_decorator=ShellBashDecorator(),
                 shell_wine_decorator=ShellWineDecorator()):
        self.__shell_cmd_decorator = shell_cmd_decorator
        self.__shell_bash_decorator = shell_bash_decorator
        self.__shell_wine_decorator = shell_wine_decorator

    def __call__(self, func):
        @self.__shell_cmd_decorator
        def __decorator_func_cmd(*args, **kwargs):
            return func(*args, **kwargs)

        @self.__shell_bash_decorator
        @self.__shell_cmd_decorator
        def __decorator_func_win_unix(*args, **kwargs):
            return func(*args, **kwargs)

        @self.__shell_bash_decorator
        @ShellBashScriptDecorator([self.__shell_wine_decorator, self.__shell_cmd_decorator], ".cmd")
        def __decorator_func_unix(*args, **kwargs):
            return func(*args, **kwargs)

        if CurrentOs.is_windows():
            return __decorator_func_cmd
        elif CurrentOs.is_msys() or CurrentOs.is_cygwin():
            return __decorator_func_win_unix
        return __decorator_func_unix
