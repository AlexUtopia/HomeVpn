import os
import pathlib

from lib.python.system import CurrentOs


# https://askubuntu.com/questions/880832/what-is-the-difference-between-wine-and-wine64
# WineHQ запускается из под bash, рекомендуется применять с ShellCmdDecorator
# https://unix.stackexchange.com/questions/801401/wine-cmd-automatically-escapes-quotes-adds-backslash
class ShellWineDecorator:
    @staticmethod
    def get_wine_executable_path() -> pathlib.Path:
        if CurrentOs.is_linux():
            wine_default = pathlib.Path("wine")
            wine_stable = pathlib.Path("/opt/wine-stable/bin/wine")
            if wine_stable.exists():
                return wine_stable
            return wine_default
        elif CurrentOs.is_termux():
            return pathlib.Path("wine-stable")
        else:
            raise Exception("[wine] Wine is not available")

    def __init__(self, wine_path: str | os.PathLike[str] = get_wine_executable_path(),
                 is_crutch_for_msys2_over_wine: bool = False):
        self.__wine_path = wine_path
        self.__is_crutch_for_msys2_over_wine = is_crutch_for_msys2_over_wine

    def __call__(self, func):
        def __decorator_func(*args, **kwargs):
            cmd_line = func(*args, **kwargs)
            return f'{self.__crutch_for_msys2_over_wine()}WINEDEBUG=-all && "{self.__wine_path}" {cmd_line}'

        return __decorator_func

    def __crutch_for_msys2_over_wine(self):
        if not self.__is_crutch_for_msys2_over_wine:
            return ""
        return f'sed -i \'s/delims=,;=	 "/delims=,;= "/g\' ~/.wine/drive_c/msys64/msys2_shell.cmd && '
