from __future__ import annotations

import asyncio
import getpass
import hashlib
import os
import shutil
import sys
from dataclasses import dataclass

from lib.python.logger import Logger
from lib.python.project import ProjectScript
from lib.python.shell import Shell
from lib.python.system import CurrentOs
from lib.python.types import JsonConfigReader
from lib.python.types import JsonConfigWriter
from lib.python.types import Path
from lib.python.types import TextConfigWriter
from lib.python.utils import AsyncRunner


@dataclass
class ExecuteMode:
    is_background_executing: bool = False
    is_execute_once: bool = False
    is_log_stdout: bool = True
    is_log_stderr: bool = True


class StartupBase:
    __STARTUP_SCRIPTS_DIR_NAME = ".startup_scripts"
    __RUN_ONCE_SCRIPT_DIR_NAME = "run_once"

    class StartupScriptMeta:
        META_FILE_EXTENSION = ".meta"

        def __init__(self, startup_script_file_path: str | os.PathLike[str],
                     execute_mode: ExecuteMode = ExecuteMode()):
            self.startup_script_meta_file_path = StartupBase.StartupScriptMeta.get_startup_script_meta_path(
                startup_script_file_path=startup_script_file_path)
            self.execute_mode = execute_mode

        def create(self):
            JsonConfigWriter(self.startup_script_meta_file_path).set(self.execute_mode.__dict__)

        def replace(self, dir_path_for_replace: str | os.PathLike[str]):
            self.startup_script_meta_file_path = self.startup_script_meta_file_path.replace(
                Path(dir_path_for_replace) / self.startup_script_meta_file_path.name)

        @staticmethod
        def get_startup_script_meta(
                startup_script_file_path: str | os.PathLike[str]) -> StartupBase.StartupScriptMeta | None:
            _startup_script_file_path = Path(startup_script_file_path)
            if _startup_script_file_path.suffix == StartupBase.StartupScriptMeta.META_FILE_EXTENSION:
                return None

            startup_script_meta_file_path = StartupBase.StartupScriptMeta.get_startup_script_meta_path(
                startup_script_file_path=_startup_script_file_path)
            if not startup_script_meta_file_path.file_exists():
                return StartupBase.StartupScriptMeta(startup_script_file_path=_startup_script_file_path)

            startup_script_meta_as_dict = JsonConfigReader(startup_script_meta_file_path).get()
            return StartupBase.StartupScriptMeta(startup_script_file_path=_startup_script_file_path,
                                                 execute_mode=ExecuteMode(**startup_script_meta_as_dict))

        @staticmethod
        def get_startup_script_meta_path(startup_script_file_path: str | os.PathLike[str]) -> Path:
            return Path(startup_script_file_path).with_suffix(StartupBase.StartupScriptMeta.META_FILE_EXTENSION)

    class StartupScript:
        __ENCODE = "utf-8"

        def __init__(self, startup_script_file_path: str | os.PathLike[str],
                     execute_mode: ExecuteMode = ExecuteMode()):
            self.path = Path(startup_script_file_path)
            self.meta = StartupBase.StartupScriptMeta(startup_script_file_path=startup_script_file_path,
                                                      execute_mode=execute_mode)

        @staticmethod
        def get(startup_script_file_path: str | os.PathLike[str]) -> StartupBase.StartupScript | None:
            startup_script_meta = StartupBase.StartupScriptMeta.get_startup_script_meta(startup_script_file_path)
            if not startup_script_meta:
                return None

            return StartupBase.StartupScript(startup_script_file_path=startup_script_file_path,
                                             execute_mode=startup_script_meta.execute_mode)

        @staticmethod
        def build(startup_script_content: str,
                  startup_script_file_extension: str,
                  startup_script_base_dir_path: str | os.PathLike[str],
                  execute_mode: ExecuteMode) -> StartupBase.StartupScript:

            startup_script_file_path = StartupBase.StartupScript.__get_startup_script_file_path(
                startup_script_content=startup_script_content,
                startup_script_file_extension=startup_script_file_extension,
                startup_script_base_dir_path=Path(startup_script_base_dir_path))

            if startup_script_file_path.file_exists():
                Logger.instance().debug(f"[Startup] Script \"{startup_script_file_path}\" ALREADY EXISTS")
                return StartupBase.StartupScript.get(startup_script_file_path=startup_script_file_path)

            result = StartupBase.StartupScript(startup_script_file_path=startup_script_file_path,
                                               execute_mode=execute_mode)
            result.create(startup_script_content=startup_script_content)
            return result

        def create(self, startup_script_content: str) -> None:
            Logger.instance().debug(
                f'[Startup] Create script "{self.path}":\n{startup_script_content}\n')
            TextConfigWriter(self.path).set(startup_script_content, set_executable=True)
            self.meta.create()

        def replace(self, dir_path_for_replace: str | os.PathLike[str]) -> Path:
            self.path = self.path.replace(
                Path(dir_path_for_replace) / self.path.name)

            self.meta.replace(dir_path_for_replace)
            return self.path

        @staticmethod
        def __get_startup_script_file_path(startup_script_content: str,
                                           startup_script_file_extension: str,
                                           startup_script_base_dir_path: Path) -> Path:
            return (startup_script_base_dir_path / StartupBase.StartupScript.__get_startup_script_name_by_content(
                startup_script_content)).with_suffix(startup_script_file_extension)

        @staticmethod
        def __get_startup_script_name_by_content(startup_script_content) -> str:
            return hashlib.md5(str(startup_script_content).encode(StartupBase.StartupScript.__ENCODE)).hexdigest()

    def __init__(self, supervisor_script_id: str, supervisor_script, user: str = getpass.getuser(),
                 startup_script_base_dir_path: str | os.PathLike[str] | None = None):
        self.__supervisor_script = supervisor_script
        self.__user = user
        self.__startup_script_base_dir_path = Path(startup_script_base_dir_path) if startup_script_base_dir_path else Path.get_home_dir_path(
            self.__user) / self.__STARTUP_SCRIPTS_DIR_NAME / supervisor_script_id

    def register_script(self, startup_script_content: str,
                        startup_script_file_extension: str = Shell().get_script_file_extension(),
                        execute_mode: ExecuteMode = ExecuteMode()) -> Path:
        self.__supervisor_script.register()
        return StartupBase.StartupScript.build(startup_script_content=startup_script_content,
                                               startup_script_file_extension=startup_script_file_extension,
                                               startup_script_base_dir_path=self.__startup_script_base_dir_path,
                                               execute_mode=execute_mode).path

    def run_all_scripts(self) -> None:
        self.__remake_execute_once_script_dir()
        script_runner = AsyncRunner()
        for path in sorted(self.__startup_script_base_dir_path.iterdir(),
                           key=lambda x: x.stat().st_mtime_ns, reverse=True):
            if path.is_file():
                startup_script = StartupBase.StartupScript.get(path)
                if startup_script:
                    if startup_script.meta.execute_mode.is_execute_once:
                        startup_script.replace(self.__get_execute_once_script_dir_path())
                    script_runner.add(Shell().get_run_script_in_shell_command_line(startup_script.path),
                                      is_background_executing=startup_script.meta.execute_mode.is_background_executing,
                                      log_stdout=startup_script.meta.execute_mode.is_log_stdout,
                                      log_stderr=startup_script.meta.execute_mode.is_log_stderr)
        asyncio.run(script_runner.run_all())
        self.__remove_execute_once_script_dir()

    def __remake_execute_once_script_dir(self) -> None:
        self.__remove_execute_once_script_dir()
        self.__get_execute_once_script_dir_path().makedirs()

    def __remove_execute_once_script_dir(self) -> None:
        shutil.rmtree(self.__get_execute_once_script_dir_path(), ignore_errors=True)

    def __get_execute_once_script_dir_path(self) -> Path:
        return self.__startup_script_base_dir_path / self.__RUN_ONCE_SCRIPT_DIR_NAME


class SupervisorScriptContent:
    RUN_SCRIPT_TEMPLATE = "run_script_template.sh"

    def __init__(self, project_script=ProjectScript(RUN_SCRIPT_TEMPLATE),
                 startup_script_base_dir_path: str | os.PathLike[str] | None = None):
        self.__project_script = project_script
        self.__startup_script_base_dir_path = startup_script_base_dir_path

    def get(self) -> str:
        result = self.__project_script.get_run_cmd_in_shell(
            f'"lib/python/startup/startup.py"{self.__get_startup_script_base_dir_path()}')
        Logger.instance().debug(f"[Startup] Register supervisor script: {result}")
        return result

    def __get_startup_script_base_dir_path(self) -> str:
        if not self.__startup_script_base_dir_path:
            return ""

        return f' "{self.__startup_script_base_dir_path}"'


class CrontabSupervisorScript:
    def __init__(self, supervisor_script_id: str, user: str = getpass.getuser(),
                 supervisor_script_content=SupervisorScriptContent()):
        self.__user = user
        self.__supervisor_script_id = supervisor_script_id
        self.__supervisor_script_content = supervisor_script_content

    def register(self) -> None:
        import crontab
        with crontab.CronTab(user=self.__user) as cron:
            if next(cron.find_comment(self.__supervisor_script_id), None) is not None:
                return

            command = self.__supervisor_script_content.get()
            job = cron.new(command=command, comment=self.__supervisor_script_id)
            job.every_reboot()


class FileSupervisorScript:
    def __init__(self, supervisor_script_id: str, user: str = getpass.getuser(),
                 supervisor_script_content=SupervisorScriptContent(),
                 supervisor_script_file_path: str | os.PathLike[str] | None = None, shell=Shell(),
                 is_rewrite_supervisor_script: bool = False):
        self.__user = user
        self.__supervisor_script_id = supervisor_script_id
        self.__supervisor_script_content = supervisor_script_content
        self.__supervisor_script_file_path = Path(
            supervisor_script_file_path) if supervisor_script_file_path else self.__get_supervisor_script_file_path_default()
        self.__shell = shell
        self.__is_rewrite_supervisor_script = is_rewrite_supervisor_script

    def register(self) -> None:
        if not self.__is_rewrite_supervisor_script and self.__supervisor_script_file_path.exists():
            return

        TextConfigWriter(self.__supervisor_script_file_path).set(
            self.__shell.make_script(self.__supervisor_script_content.get()), set_executable=True)

    def __get_supervisor_script_file_path_default(self) -> Path:
        return self.__get_supervisor_script_dir_path_default() / f"startup_{sys.platform}_{self.__supervisor_script_id}{self.__shell.get_script_file_extension()}"

    # https://superuser.com/a/1518663/2121020
    def __get_supervisor_script_dir_path_default(self) -> Path:
        return Path.get_windows_home_dir_path(
            self.__user) / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup"


class Startup:
    SUPERVISOR_SCRIPT_ID = "da7f518c-2839-4a29-bc34-904c0d786a14"

    def __init__(self, user: str = getpass.getuser(), startup_script_base_dir_path: str | os.PathLike[str] | None = None):
        if CurrentOs.is_linux():
            self.__startup_impl = StartupBase(
                supervisor_script_id=Startup.SUPERVISOR_SCRIPT_ID,
                supervisor_script=CrontabSupervisorScript(
                    supervisor_script_id=Startup.SUPERVISOR_SCRIPT_ID,
                    user=user,
                    supervisor_script_content=SupervisorScriptContent(startup_script_base_dir_path=startup_script_base_dir_path)),
                user=user,
                startup_script_base_dir_path=startup_script_base_dir_path)
        elif CurrentOs.is_windows_platform():
            self.__startup_impl = StartupBase(
                supervisor_script_id=Startup.SUPERVISOR_SCRIPT_ID,
                supervisor_script=FileSupervisorScript(
                    supervisor_script_id=Startup.SUPERVISOR_SCRIPT_ID,
                    user=user,
                    supervisor_script_content=SupervisorScriptContent(startup_script_base_dir_path=startup_script_base_dir_path),
                    shell=Shell(is_windows=True)),
                user=user,
                startup_script_base_dir_path=startup_script_base_dir_path)
        else:
            raise Exception("[Startup] NOT IMPLEMENTED")

    def register_script(self, startup_script_content: str,
                        startup_script_file_extension: str = Shell().get_script_file_extension(),
                        execute_mode: ExecuteMode = ExecuteMode()) -> Path:
        return self.__startup_impl.register_script(startup_script_content=startup_script_content,
                                                   startup_script_file_extension=startup_script_file_extension,
                                                   execute_mode=execute_mode)

    def run_all_scripts(self) -> None:
        self.__startup_impl.run_all_scripts()


if __name__ == '__main__':
    __startup_script_base_dir_path = sys.argv[1] if len(sys.argv) > 1 else None
    Startup(startup_script_base_dir_path=__startup_script_base_dir_path).run_all_scripts()
