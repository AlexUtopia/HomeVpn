"""Регистрация и запуск скриптов при старте системы"""

from __future__ import annotations

import asyncio
import getpass
import hashlib
import os
import shutil
import sys
import typing
from dataclasses import dataclass

import crontab

from lib.python.logger.logger import Logger
from lib.python.project.project_script import ProjectScript
from lib.python.shell.shell import Shell
from lib.python.system.current_os import CurrentOs
from lib.python.types.json import JsonType
from lib.python.types.path import Path
from lib.python.types.text_reader import JsonConfigReader
from lib.python.types.text_writer import JsonConfigWriter, TextConfigWriter
from lib.python.utils.async_runner import AsyncRunner


class SupervisorScriptProtocol(typing.Protocol):
    """Протокол супервизор-скрипта"""

    def register(self) -> None:
        """Зарегистрировать супервизор-скрипт"""
        ...


@dataclass
class ExecuteMode:
    """Режим выполнения скрипта при старте системы"""

    is_background_executing: bool = False
    is_execute_once: bool = False
    is_log_stdout: bool = True
    is_log_stderr: bool = True


class StartupBase:
    """Базовый механизм регистрации и запуска скриптов при старте системы"""

    __STARTUP_SCRIPTS_DIR_NAME = ".startup_scripts"
    __RUN_ONCE_SCRIPT_DIR_NAME = "run_once"

    class StartupScriptMeta:
        """Метаданные скрипта запуска"""

        META_FILE_EXTENSION = ".meta"

        def __init__(self, startup_script_file_path: str | os.PathLike[str],
                     execute_mode: ExecuteMode = ExecuteMode()) -> None:
            """Инициализировать метаданные скрипта

            :param startup_script_file_path: Путь до скрипта запуска
            :param execute_mode: Режим выполнения скрипта
            """
            self.startup_script_meta_file_path = StartupBase.StartupScriptMeta.get_startup_script_meta_path(
                startup_script_file_path=startup_script_file_path)
            self.execute_mode = execute_mode

        def create(self) -> None:
            """Создать файл метаданных"""
            JsonConfigWriter(self.startup_script_meta_file_path).set(self.execute_mode.__dict__)

        def replace(self, dir_path_for_replace: str | os.PathLike[str]) -> None:
            """Переместить файл метаданных в другую директорию

            :param dir_path_for_replace: Целевая директория
            """
            self.startup_script_meta_file_path = self.startup_script_meta_file_path.replace(
                Path(dir_path_for_replace) / self.startup_script_meta_file_path.name)

        @staticmethod
        def get_startup_script_meta(
                startup_script_file_path: str | os.PathLike[str]) -> StartupBase.StartupScriptMeta | None:
            """Получить метаданные скрипта запуска

            :param startup_script_file_path: Путь до скрипта запуска
            :return: Метаданные скрипта или ``None``, если передан файл метаданных
            """
            _startup_script_file_path = Path(startup_script_file_path)
            if _startup_script_file_path.suffix == StartupBase.StartupScriptMeta.META_FILE_EXTENSION:
                return None

            startup_script_meta_file_path = StartupBase.StartupScriptMeta.get_startup_script_meta_path(
                startup_script_file_path=_startup_script_file_path)
            if not startup_script_meta_file_path.file_exists():
                return StartupBase.StartupScriptMeta(startup_script_file_path=_startup_script_file_path)

            startup_script_meta_as_dict = JsonConfigReader(startup_script_meta_file_path).get()
            if not isinstance(startup_script_meta_as_dict, dict):
                raise RuntimeError(f"[Startup] Invalid meta file: {startup_script_meta_file_path}")

            return StartupBase.StartupScriptMeta(
                startup_script_file_path=_startup_script_file_path,
                execute_mode=StartupBase.StartupScriptMeta._get_execute_mode(startup_script_meta_as_dict))

        @staticmethod
        def get_startup_script_meta_path(startup_script_file_path: str | os.PathLike[str]) -> Path:
            """Получить путь до файла метаданных скрипта запуска

            :param startup_script_file_path: Путь до скрипта запуска
            :return: Путь до файла метаданных
            """
            return Path(startup_script_file_path).with_suffix(StartupBase.StartupScriptMeta.META_FILE_EXTENSION)

        @staticmethod
        def _get_execute_mode(meta: dict[str, JsonType]) -> ExecuteMode:
            """Собрать режим выполнения из метаданных

            :param meta: Метаданные скрипта
            :return: Режим выполнения скрипта
            """
            default = ExecuteMode()
            return ExecuteMode(
                is_background_executing=bool(meta.get("is_background_executing", default.is_background_executing)),
                is_execute_once=bool(meta.get("is_execute_once", default.is_execute_once)),
                is_log_stdout=bool(meta.get("is_log_stdout", default.is_log_stdout)),
                is_log_stderr=bool(meta.get("is_log_stderr", default.is_log_stderr)))

    class StartupScript:
        """Скрипт запуска"""

        __ENCODE = "utf-8"

        def __init__(self, startup_script_file_path: str | os.PathLike[str],
                     execute_mode: ExecuteMode = ExecuteMode()) -> None:
            """Инициализировать скрипт запуска

            :param startup_script_file_path: Путь до скрипта запуска
            :param execute_mode: Режим выполнения скрипта
            """
            self.path = Path(startup_script_file_path)
            self.meta = StartupBase.StartupScriptMeta(startup_script_file_path=startup_script_file_path,
                                                      execute_mode=execute_mode)

        @staticmethod
        def get(startup_script_file_path: str | os.PathLike[str]) -> StartupBase.StartupScript | None:
            """Получить скрипт запуска по пути

            :param startup_script_file_path: Путь до скрипта запуска
            :return: Скрипт запуска или ``None``, если метаданные не найдены
            """
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
            """Создать скрипт запуска с указанным содержимым

            :param startup_script_content: Содержимое скрипта
            :param startup_script_file_extension: Расширение файла скрипта
            :param startup_script_base_dir_path: Базовая директория скриптов запуска
            :param execute_mode: Режим выполнения скрипта
            :return: Созданный скрипт запуска
            """
            startup_script_file_path = StartupBase.StartupScript._get_startup_script_file_path(
                startup_script_content=startup_script_content,
                startup_script_file_extension=startup_script_file_extension,
                startup_script_base_dir_path=Path(startup_script_base_dir_path))

            if startup_script_file_path.file_exists():
                Logger.instance().debug('[Startup] Script "%s" ALREADY EXISTS', startup_script_file_path)
                existing_script = StartupBase.StartupScript.get(startup_script_file_path=startup_script_file_path)
                if existing_script is not None:
                    return existing_script

            result = StartupBase.StartupScript(startup_script_file_path=startup_script_file_path,
                                               execute_mode=execute_mode)
            result.create(startup_script_content=startup_script_content)
            return result

        def create(self, startup_script_content: str) -> None:
            """Создать файл скрипта запуска

            :param startup_script_content: Содержимое скрипта
            """
            Logger.instance().debug('[Startup] Create script "%s":\n%s\n', self.path, startup_script_content)
            TextConfigWriter(self.path).set(startup_script_content, set_executable=True)
            self.meta.create()

        def replace(self, dir_path_for_replace: str | os.PathLike[str]) -> Path:
            """Переместить скрипт запуска в другую директорию

            :param dir_path_for_replace: Целевая директория
            :return: Новый путь до скрипта
            """
            self.path = self.path.replace(
                Path(dir_path_for_replace) / self.path.name)

            self.meta.replace(dir_path_for_replace)
            return self.path

        @staticmethod
        def _get_startup_script_file_path(startup_script_content: str,
                                          startup_script_file_extension: str,
                                          startup_script_base_dir_path: Path) -> Path:
            """Получить путь до файла скрипта запуска

            :param startup_script_content: Содержимое скрипта
            :param startup_script_file_extension: Расширение файла скрипта
            :param startup_script_base_dir_path: Базовая директория скриптов запуска
            :return: Путь до файла скрипта
            """
            return (startup_script_base_dir_path / StartupBase.StartupScript._get_startup_script_name_by_content(
                startup_script_content)).with_suffix(startup_script_file_extension)

        @staticmethod
        def _get_startup_script_name_by_content(startup_script_content: str) -> str:
            """Получить имя скрипта по его содержимому

            :param startup_script_content: Содержимое скрипта
            :return: Имя скрипта
            """
            return hashlib.md5(startup_script_content.encode(StartupBase.StartupScript.__ENCODE)).hexdigest()

    def __init__(self, supervisor_script_id: str, supervisor_script: SupervisorScriptProtocol,
                 user: str = getpass.getuser(),
                 startup_script_base_dir_path: str | os.PathLike[str] | None = None) -> None:
        """Инициализировать механизм запуска скриптов

        :param supervisor_script_id: Идентификатор супервизор-скрипта
        :param supervisor_script: Супервизор-скрипт
        :param user: Пользователь, от имени которого запускаются скрипты
        :param startup_script_base_dir_path: Базовая директория скриптов запуска
        :raises RuntimeError: Если домашняя директория пользователя не найдена
        """
        self.__supervisor_script = supervisor_script
        self.__user = user

        if startup_script_base_dir_path:
            self.__startup_script_base_dir_path = Path(startup_script_base_dir_path)
        else:
            home_dir_path = Path.get_home_dir_path(self.__user)
            if home_dir_path is None:
                raise RuntimeError(f"[Startup] Home directory NOT FOUND for user \"{self.__user}\"")
            self.__startup_script_base_dir_path = home_dir_path / self.__STARTUP_SCRIPTS_DIR_NAME / supervisor_script_id

    def register_script(self, startup_script_content: str,
                        startup_script_file_extension: str = Shell().get_script_file_extension(),
                        execute_mode: ExecuteMode = ExecuteMode()) -> Path:
        """Зарегистрировать скрипт запуска

        :param startup_script_content: Содержимое скрипта
        :param startup_script_file_extension: Расширение файла скрипта
        :param execute_mode: Режим выполнения скрипта
        :return: Путь до зарегистрированного скрипта
        """
        self.__supervisor_script.register()
        return StartupBase.StartupScript.build(startup_script_content=startup_script_content,
                                               startup_script_file_extension=startup_script_file_extension,
                                               startup_script_base_dir_path=self.__startup_script_base_dir_path,
                                               execute_mode=execute_mode).path

    def run_all_scripts(self) -> None:
        """Запустить все зарегистрированные скрипты"""
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
        """Пересоздать директорию скриптов, выполняемых один раз"""
        self.__remove_execute_once_script_dir()
        self.__get_execute_once_script_dir_path().makedirs()

    def __remove_execute_once_script_dir(self) -> None:
        """Удалить директорию скриптов, выполняемых один раз"""
        shutil.rmtree(self.__get_execute_once_script_dir_path(), ignore_errors=True)

    def __get_execute_once_script_dir_path(self) -> Path:
        """Получить путь до директории скриптов, выполняемых один раз

        :return: Путь до директории
        """
        return self.__startup_script_base_dir_path / self.__RUN_ONCE_SCRIPT_DIR_NAME


class SupervisorScriptContent:
    """Содержимое супервизор-скрипта"""

    RUN_SCRIPT_TEMPLATE = "run_script_template.sh"

    def __init__(self, project_script: ProjectScript = ProjectScript(RUN_SCRIPT_TEMPLATE),
                 startup_script_base_dir_path: str | os.PathLike[str] | None = None) -> None:
        """Инициализировать содержимое супервизор-скрипта

        :param project_script: Скрипт проекта
        :param startup_script_base_dir_path: Базовая директория скриптов запуска
        """
        self.__project_script = project_script
        self.__startup_script_base_dir_path = startup_script_base_dir_path

    def get(self) -> str:
        """Получить содержимое супервизор-скрипта

        :return: Содержимое супервизор-скрипта
        """
        result = self.__project_script.get_run_cmd_in_shell(
            f'"lib/python/startup/startup.py"{self.__get_startup_script_base_dir_path()}')
        Logger.instance().debug("[Startup] Register supervisor script: %s", result)
        return result

    def __get_startup_script_base_dir_path(self) -> str:
        """Получить аргумент командной строки с базовой директорией скриптов

        :return: Аргумент командной строки или пустая строка
        """
        if not self.__startup_script_base_dir_path:
            return ""

        return f' "{self.__startup_script_base_dir_path}"'


class CrontabSupervisorScript:
    """Супервизор-скрипт на основе crontab"""

    def __init__(self, supervisor_script_id: str, user: str = getpass.getuser(),
                 supervisor_script_content: SupervisorScriptContent = SupervisorScriptContent()) -> None:
        """Инициализировать супервизор-скрипт

        :param supervisor_script_id: Идентификатор супервизор-скрипта
        :param user: Пользователь, от имени которого запускаются скрипты
        :param supervisor_script_content: Содержимое супервизор-скрипта
        """
        self.__user = user
        self.__supervisor_script_id = supervisor_script_id
        self.__supervisor_script_content = supervisor_script_content

    def register(self) -> None:
        """Зарегистрировать задание в crontab"""
        with crontab.CronTab(user=self.__user) as cron:
            if next(cron.find_comment(self.__supervisor_script_id), None) is not None:
                return

            command = self.__supervisor_script_content.get()
            job = cron.new(command=command, comment=self.__supervisor_script_id)
            job.every_reboot()


class FileSupervisorScript:
    """Супервизор-скрипт на основе файла автозапуска"""

    def __init__(self, supervisor_script_id: str, user: str = getpass.getuser(),
                 supervisor_script_content: SupervisorScriptContent = SupervisorScriptContent(),
                 supervisor_script_file_path: str | os.PathLike[str] | None = None,
                 is_rewrite_supervisor_script: bool = False) -> None:
        """Инициализировать супервизор-скрипт

        :param supervisor_script_id: Идентификатор супервизор-скрипта
        :param user: Пользователь, от имени которого запускаются скрипты
        :param supervisor_script_content: Содержимое супервизор-скрипта
        :param supervisor_script_file_path: Путь до файла супервизор-скрипта
        :param is_rewrite_supervisor_script: Перезаписывать существующий супервизор-скрипт
        """
        self.__user = user
        self.__supervisor_script_id = supervisor_script_id
        self.__supervisor_script_content = supervisor_script_content
        self.__shell = Shell(is_windows=CurrentOs.is_windows_platform())
        self.__is_rewrite_supervisor_script = is_rewrite_supervisor_script
        self.__supervisor_script_file_path = (Path(supervisor_script_file_path)
                                              if supervisor_script_file_path
                                              else self.__get_supervisor_script_file_path_default())

    def register(self) -> None:
        """Создать файл супервизор-скрипта"""
        if not self.__is_rewrite_supervisor_script and self.__supervisor_script_file_path.exists():
            return

        TextConfigWriter(self.__supervisor_script_file_path).set(
            self.__shell.make_script(self.__supervisor_script_content.get()), set_executable=True)

    def __get_supervisor_script_file_path_default(self) -> Path:
        """Получить путь до файла супервизор-скрипта по умолчанию

        :return: Путь до файла супервизор-скрипта
        """
        return self.__get_supervisor_script_dir_path_default() / \
            f"startup_{sys.platform}_{self.__supervisor_script_id}{self.__shell.get_script_file_extension()}"

    # https://superuser.com/a/1518663/2121020
    def __get_supervisor_script_dir_path_default(self) -> Path:
        """Получить директорию автозапуска по умолчанию

        :return: Путь до директории автозапуска
        :raises RuntimeError: Если домашняя директория пользователя не найдена
        """
        home_dir_path = Path.get_windows_home_dir_path(self.__user)
        if home_dir_path is None:
            raise RuntimeError(f"[Startup] Home directory NOT FOUND for user \"{self.__user}\"")
        return home_dir_path / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup"


class Startup:
    """Регистрация и запуск скриптов при старте системы"""

    SUPERVISOR_SCRIPT_ID = "da7f518c-2839-4a29-bc34-904c0d786a14"

    def __init__(self, user: str = getpass.getuser(),
                 startup_script_base_dir_path: str | os.PathLike[str] | None = None) -> None:
        """Инициализировать механизм запуска скриптов

        :param user: Пользователь, от имени которого запускаются скрипты
        :param startup_script_base_dir_path: Базовая директория скриптов запуска
        :raises RuntimeError: Если платформа не поддерживается
        """
        if CurrentOs.is_linux():
            self.__startup_impl = StartupBase(
                supervisor_script_id=Startup.SUPERVISOR_SCRIPT_ID,
                supervisor_script=CrontabSupervisorScript(
                    supervisor_script_id=Startup.SUPERVISOR_SCRIPT_ID,
                    user=user,
                    supervisor_script_content=SupervisorScriptContent(
                        startup_script_base_dir_path=startup_script_base_dir_path)),
                user=user,
                startup_script_base_dir_path=startup_script_base_dir_path)
        elif CurrentOs.is_windows_platform():
            self.__startup_impl = StartupBase(
                supervisor_script_id=Startup.SUPERVISOR_SCRIPT_ID,
                supervisor_script=FileSupervisorScript(
                    supervisor_script_id=Startup.SUPERVISOR_SCRIPT_ID,
                    user=user,
                    supervisor_script_content=SupervisorScriptContent(
                        startup_script_base_dir_path=startup_script_base_dir_path)),
                user=user,
                startup_script_base_dir_path=startup_script_base_dir_path)
        else:
            raise RuntimeError("[Startup] NOT IMPLEMENTED")

    def register_script(self, startup_script_content: str,
                        startup_script_file_extension: str = Shell().get_script_file_extension(),
                        execute_mode: ExecuteMode = ExecuteMode()) -> Path:
        """Зарегистрировать скрипт запуска

        :param startup_script_content: Содержимое скрипта
        :param startup_script_file_extension: Расширение файла скрипта
        :param execute_mode: Режим выполнения скрипта
        :return: Путь до зарегистрированного скрипта
        """
        return self.__startup_impl.register_script(startup_script_content=startup_script_content,
                                                   startup_script_file_extension=startup_script_file_extension,
                                                   execute_mode=execute_mode)

    def run_all_scripts(self) -> None:
        """Запустить все зарегистрированные скрипты"""
        self.__startup_impl.run_all_scripts()


if __name__ == '__main__':
    __startup_script_base_dir_path = sys.argv[1] if len(sys.argv) > 1 else None
    Startup(startup_script_base_dir_path=__startup_script_base_dir_path).run_all_scripts()
