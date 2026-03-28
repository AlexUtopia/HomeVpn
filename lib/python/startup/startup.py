from __future__ import annotations

import asyncio
import getpass
import hashlib
import re
import shutil
import sys

from lib.python.logger import Logger
from lib.python.project import ProjectScript
from lib.python.shell import Shell
from lib.python.system import CurrentOs
from lib.python.types import Path
from lib.python.utils import AsyncRunner


class StartupCrontab:
    SUPERVISOR_SCRIPT_ID = "da7f518c-2839-4a29-bc34-904c0d786a14"

    __STARTUP_SCRIPTS_DIR_NAME = ".startup_scripts"
    __RUN_ONCE_SCRIPT_DIR_NAME = "run_once"

    class StartupScriptName:
        __ENCODE = "utf-8"
        __NAME = "name"
        __IS_BACKGROUND_EXECUTING_LABEL = "_bg"
        __IS_BACKGROUND_EXECUTING = "is_background_executing"
        __IS_EXECUTE_ONCE_LABEL = "_once"
        __IS_EXECUTE_ONCE = "is_execute_once"
        __STARTUP_SCRIPT_FILE_EXTENSION = "startup_script_file_extension"

        __REGEX_MD5 = "[a-f0-9]{32}"
        __REGEX = fr"(?P<{__NAME}>{__REGEX_MD5})(?P<{__IS_BACKGROUND_EXECUTING}>{__IS_BACKGROUND_EXECUTING_LABEL})?(?P<{__IS_EXECUTE_ONCE}>{__IS_EXECUTE_ONCE_LABEL})?\(?P<{__STARTUP_SCRIPT_FILE_EXTENSION}>{__STARTUP_SCRIPT_FILE_EXTENSION})"

        def __init__(self, is_background_executing: bool, is_execute_once: bool, startup_script_content: str | None,
                     startup_script_file_extension: str, name: str | None = None):
            self.is_background_executing = is_background_executing
            self.is_execute_once = is_execute_once
            self.startup_script_file_extension = startup_script_file_extension
            self.name = name if isinstance(name, str) else self.__get_startup_script_name_by_content(
                startup_script_content)

        def __str__(self):
            return self.get()

        def __repr__(self):
            return self.__str__()

        def get(self) -> str:
            return f"{self.name}{self.__get_background_executing_prefix()}{self.__get_execute_once_prefix()}{self.startup_script_file_extension}"

        def get_wildcard(self) -> str:
            return f"{self.name}*{self.startup_script_file_extension}"

        def __get_startup_script_name_by_content(self, startup_script_content) -> str:
            return hashlib.md5(str(startup_script_content).encode(self.__ENCODE)).hexdigest()

        def __get_background_executing_prefix(self) -> str:
            return self.__IS_BACKGROUND_EXECUTING_LABEL if self.is_background_executing else ""

        def __get_execute_once_prefix(self) -> str:
            return self.__IS_EXECUTE_ONCE_LABEL if self.is_execute_once else ""

        @staticmethod
        def parse(startup_script_file_name) -> StartupCrontab.StartupScriptName | None:
            regex = re.compile(StartupCrontab.StartupScriptName.__REGEX)
            match = regex.fullmatch(startup_script_file_name)
            if not match:
                return None

            name = match.group(StartupCrontab.StartupScriptName.__NAME)
            is_background_executing = bool(match.group(StartupCrontab.StartupScriptName.__IS_BACKGROUND_EXECUTING))
            is_execute_once = bool(match.group(StartupCrontab.StartupScriptName.__IS_EXECUTE_ONCE))
            startup_script_file_extension = match.group(
                StartupCrontab.StartupScriptName.__STARTUP_SCRIPT_FILE_EXTENSION)

            return StartupCrontab.StartupScriptName(is_background_executing=is_background_executing,
                                                    is_execute_once=is_execute_once, startup_script_content=None,
                                                    startup_script_file_extension=startup_script_file_extension,
                                                    name=name)

    def __init__(self, user: str = getpass.getuser()):
        self.__user = user

    def register_script(self, startup_script_content: str,
                        startup_script_file_extension: str = Shell().get_script_file_extension(),
                        is_background_executing: bool = False,
                        is_execute_once: bool = False) -> bool:
        self._register_supervisor_script()
        startup_script_name = StartupCrontab.StartupScriptName(is_background_executing=is_background_executing,
                                                               is_execute_once=is_execute_once,
                                                               startup_script_content=startup_script_content,
                                                               startup_script_file_extension=startup_script_file_extension)
        return self._create_startup_script_file(startup_script_name, startup_script_content)

    def run_all_scripts(self) -> None:
        self._remake_execute_once_script_dir()
        script_runner = AsyncRunner()
        for path in sorted(self._get_startup_script_dir_path().glob("*"),
                           key=lambda x: x.stat().st_mtime_ns, reverse=True):
            if path.is_file():
                startup_script_name = StartupCrontab.StartupScriptName.parse(path.name)
                if startup_script_name:
                    if startup_script_name.is_execute_once:
                        path = path.replace(self._get_execute_once_script_dir_path() / path.name)
                    script_runner.add(Shell().get_run_script_in_shell_command_line(path),
                                      startup_script_name.is_background_executing)
        asyncio.run(script_runner.run_all())
        self._remove_execute_once_script_dir()

    def _remake_execute_once_script_dir(self) -> None:
        self._remove_execute_once_script_dir()
        self._get_execute_once_script_dir_path().makedirs()

    def _remove_execute_once_script_dir(self) -> None:
        shutil.rmtree(self._get_execute_once_script_dir_path(), ignore_errors=True)

    def _register_supervisor_script(self) -> None:
        import crontab
        with crontab.CronTab(user=self.__user) as cron:
            if next(cron.find_comment(self.SUPERVISOR_SCRIPT_ID), None) is not None:
                return

            command = self._get_supervisor_script_content()
            job = cron.new(command=command, comment=self.SUPERVISOR_SCRIPT_ID)
            job.every_reboot()

    def _get_supervisor_script_content(self) -> str:
        result = ProjectScript("run_script_template.sh").get_run_cmd_in_shell('"lib/python/startup/__main__.py"')
        Logger.instance().debug(f"[Startup] Register supervisor script: {result}")
        return result

    def _create_startup_script_file(self, startup_script_name: StartupScriptName, startup_script_content: str) -> bool:
        startup_script_file_path = self._get_startup_script_file_path(startup_script_name)
        if self._is_startup_script_file_exists(startup_script_name):
            Logger.instance().debug(f"[Startup] Script \"{startup_script_file_path}\" ALREADY EXISTS")
            return False

        Logger.instance().debug(f"[Startup] Create script \"{startup_script_file_path}\":\n{startup_script_content}\n")
        TextConfigWriter(startup_script_file_path).set(startup_script_content, set_executable=True)
        return True

    def _get_startup_script_file_path(self, startup_script_name: StartupScriptName) -> Path:
        return self._get_startup_script_dir_path() / str(startup_script_name)

    def _is_startup_script_file_exists(self, startup_script_name: StartupScriptName) -> bool:
        return self._get_startup_script_dir_path().exists_by_wildcard(startup_script_name.get_wildcard())

    def _get_execute_once_script_dir_path(self) -> Path:
        return self._get_startup_script_dir_path() / self.__RUN_ONCE_SCRIPT_DIR_NAME

    def _get_startup_script_dir_path(self) -> Path:
        return Path.get_home_dir_path(self.__user) / self.__STARTUP_SCRIPTS_DIR_NAME


# Windows startup
# https://superuser.com/a/1518663/2121020
class StartupWindows(StartupCrontab):
    def __init__(self, user: str = getpass.getuser()):
        super().__init__(user)
        self.__shell = Shell(is_windows=True)

    def _register_supervisor_script(self) -> None:
        supervisor_script_file_path = self.__get_supervisor_script_file_path()
        if supervisor_script_file_path.exists():
            return

        TextConfigWriter(supervisor_script_file_path).set(
            self.__shell.make_script(self._get_supervisor_script_content()))

    def __get_supervisor_script_file_path(self) -> Path:
        return self.__get_startup_dir_path() / f"startup_{sys.platform}_{self.SUPERVISOR_SCRIPT_ID}{self.__shell.get_script_file_extension()}"

    def __get_startup_dir_path(self) -> Path:
        return Path.get_home_dir_path(self.__user) / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup"


class Startup:
    def __init__(self, user: str = getpass.getuser()):
        if CurrentOs.is_linux():
            self.__startup_impl = StartupCrontab(user)
        elif CurrentOs.is_windows_platform():
            self.__startup_impl = StartupWindows(user)
        else:
            raise Exception("[Startup] NOT IMPLEMENTED")

    def register_script(self, startup_script_content: str,
                        startup_script_file_extension: str = Shell().get_script_file_extension(),
                        is_background_executing: bool = False,
                        is_execute_once: bool = False) -> bool:
        return self.__startup_impl.register_script(startup_script_content=startup_script_content,
                                                   startup_script_file_extension=startup_script_file_extension,
                                                   is_background_executing=is_background_executing,
                                                   is_execute_once=is_execute_once)

    def run_all_scripts(self) -> None:
        self.__startup_impl.run_all_scripts()
