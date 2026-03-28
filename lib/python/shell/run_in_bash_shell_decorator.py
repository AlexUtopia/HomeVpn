from lib.python.system import CurrentOs

from shell_bash_decorator import ShellBashDecorator
from shell_cmd_decorator import ShellCmdDecorator
from shell_msys2_decorator import ShellMsys2Decorator


class RunInBashShellDecorator:
    WIN_BASH_AUTO_SELECT_EXECUTE_NOW = 0
    WIN_BASH_AUTO_SELECT = 1
    WIN_BASH_MSYS2 = 2
    WIN_BASH_CYGWIN = 3

    def __init__(self, win_bash=WIN_BASH_AUTO_SELECT_EXECUTE_NOW, shell_bash_decorator=ShellBashDecorator(),
                 shell_cmd_decorator=ShellCmdDecorator(), shell_msys2_decorator=ShellMsys2Decorator()):
        self.__win_bash = win_bash
        self.__shell_bash_decorator = shell_bash_decorator
        self.__shell_cmd_decorator = shell_cmd_decorator
        self.__shell_msys2_decorator = shell_msys2_decorator

    def __call__(self, func):
        @self.__shell_bash_decorator
        def __decorator_func_bash(*args, **kwargs):
            return func(*args, **kwargs)

        @self.__shell_cmd_decorator
        @self.__shell_msys2_decorator
        def __decorator_func_msys2(*args, **kwargs):
            return __decorator_func_bash(*args, **kwargs)

        @self.__shell_cmd_decorator
        # @ShellCygwinDecorator fixme utopia Реализовать
        def __decorator_func_cygwin(*args, **kwargs):
            return __decorator_func_bash(*args, **kwargs)

        if CurrentOs.is_windows_platform():
            if self.__win_bash == self.WIN_BASH_AUTO_SELECT_EXECUTE_NOW:
                if CurrentOs.is_msys():
                    return __decorator_func_bash
                if CurrentOs.is_cygwin():
                    return __decorator_func_bash
                else:
                    raise Exception("[bash] Windows bash NOT AVAILABLE")
            elif self.__win_bash == self.WIN_BASH_AUTO_SELECT:
                if CurrentOs.is_msys():
                    return __decorator_func_msys2
                if CurrentOs.is_cygwin():
                    return __decorator_func_cygwin
                else:
                    raise Exception("[bash] Windows bash NOT AVAILABLE")
            else:
                if self.__win_bash == self.WIN_BASH_MSYS2:
                    return __decorator_func_msys2
                if self.__win_bash == self.WIN_BASH_CYGWIN:
                    return __decorator_func_cygwin
                else:
                    raise Exception("[bash] Windows bash NOT SUPPORTED")
        else:
            return __decorator_func_bash
