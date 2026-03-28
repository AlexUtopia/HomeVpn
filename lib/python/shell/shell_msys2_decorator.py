import os
import pathlib
import subprocess

from lib.python.logger import Logger
from lib.python.system import CurrentOs
from shell_bash_decorator import ShellBashDecorator
from shell_cmd_decorator import ShellCmdDecorator


# C:\msys64\msys2_shell.cmd -no-start -defterm -clang64 -c "echo gggg"
# sudo docker run -it ghcr.io/msys2/msys2-docker-experimental bash
# https://github.com/msys2/MSYS2-packages/blob/master/filesystem/msys2_shell.cmd#L92C1-L92C66
# sudo docker --user=utopia run -it ghcr.io/msys2/msys2-docker-experimental bash -c "WINEDEBUG=-all; wine cmd.exe /q /c \"C:\\\\msys64\\\\msys2_shell.cmd -no-start -defterm -clang64 -c \\\"echo gggg\\\"\""
# + заменить строку при помощи sed (костыль чтобы работало)
# sed -i 's/delims=,;=	 "/delims=,;= "/g' "~/.wine/drive_c/msys64/msys2_shell.cmd"
# for /f "tokens=%msys2_shiftCounter%,* delims=,;=	 " %%i in ("!msys2_full_cmd!") do set SHELL_ARGS=%%j
# на
# for /f "tokens=%msys2_shiftCounter%,* delims=,;= " %%i in ("!msys2_full_cmd!") do set SHELL_ARGS=%%j
# https://github.com/msys2/msys2-docker/pkgs/container/msys2-docker-experimental
class ShellMsys2Decorator:

    @staticmethod
    def get_msys2_shell() -> os.PathLike[str]:
        if CurrentOs.is_msys():
            call_result = subprocess.run("cygpath -m /", shell=True, capture_output=True, text=True)
            if call_result.returncode:
                return pathlib.Path(call_result.stdout) / "msys2_shell.cmd"
            else:
                Logger.instance().warning("[msys2] Get msys2_shell.cmd path from cygpath FAIL, use default")
        return pathlib.Path(r"%SYSTEMDRIVE%/msys64/msys2_shell.cmd")

    @staticmethod
    def get_msys2_environment() -> str:
        if CurrentOs.is_msys():
            return os.environ["MSYSTEM"].lower()
        else:
            if CurrentOs.check_arch("x86_64"):
                return "clang64"
            elif CurrentOs.check_arch("aarch64"):
                return "clangarm64"
            else:
                raise Exception("[msys2] Platform NO SUPPORT")

    def __init__(self, msys2_shell_script_path: str | os.PathLike[str] = get_msys2_shell(),
                 msys2_environment: str = get_msys2_environment()):
        self.__msys2_shell_script_path = pathlib.Path(msys2_shell_script_path)
        self.__msys2_environment = msys2_environment

    def __call__(self, func):
        def __decorator_func(*args, **kwargs):
            cmd_line = func(*args, **kwargs)
            cmd_line = ShellBashDecorator().escape_cmd_line_for_win(cmd_line)
            cmd_line = ShellCmdDecorator().full_escape_cmd_line(cmd_line)
            return f'"{self.__msys2_shell_script_path}" -no-start -{self.__msys2_environment} -defterm -c "{cmd_line}"'

        return __decorator_func
