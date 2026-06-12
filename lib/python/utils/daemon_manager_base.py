import atexit
import psutil
import shlex
import subprocess

from lib.python.logger import Logger


class DaemonManagerBase:
    def __init__(self, label: str, action: str):
        self.__label = label
        self.__action = action
        self.__command_line = None
        atexit.register(self.clear_at_exit)

    def start(self) -> None:
        if self.__command_line:
            return

        self._start_impl()
        self.__command_line = str(self._build_command_line())

        Logger.instance().debug(f"[{self.__label}] {self.__action} cmd: {self.__command_line}")
        subprocess.check_call(self.__command_line, shell=True)

    def close(self) -> None:
        if not self.__command_line:
            return

        self.__find_and_kill_target_processes()
        self._close_impl()
        self.__command_line = None

    def clear_at_exit(self) -> None:
        try:
            self.close()
        except Exception as ex:
            Logger.instance().error(f"[{self.__label}] FAIL: {ex}")

    def __find_and_kill_target_processes(self) -> None:
        for process in psutil.process_iter():
            try:
                if self.__compare_cmd_line(process.cmdline()):
                    Logger.instance().debug(f"[{self.__label}] KILL: {process}")
                    process.kill()
            except Exception:
                pass

    def __compare_cmd_line(self, psutil_process_cmdline: list[str]) -> bool:
        normalize_command_line = " ".join(shlex.split(self.__command_line))
        psutil_command_line = " ".join(psutil_process_cmdline)
        return psutil_command_line.endswith(normalize_command_line)
