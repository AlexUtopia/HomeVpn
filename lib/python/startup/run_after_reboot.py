"""Выполнение обработчика после перезагрузки"""

import inspect
import os
import pathlib
import pickle
import sys
import tempfile
import types
import typing

from lib.python.power.power import Power
from lib.python.project.project_script import ProjectScript
from lib.python.startup.startup import ExecuteMode, Startup, StartupBase
from lib.python.types.path import Path

type AfterRebootHandler = typing.Callable[[], None]


class RunAfterReboot:
    """Регистрация и выполнение обработчика после перезагрузки

    .. note::
       Обработчик не может быть lambda-выражением: для восстановления после
       перезагрузки используется pickle
    """

    def __init__(self, startup: Startup | StartupBase = Startup(),
                 pickle_dumps_dir_path: str | os.PathLike[str] = Path("data/execute_after_reboot")) -> None:
        """Инициализировать механизм выполнения после перезагрузки

        :param startup: Механизм запуска скриптов при старте системы
        :param pickle_dumps_dir_path: Директория для pickle-дампов
        """
        self.__startup = startup
        self.__pickle_dumps_dir_path = Path(pickle_dumps_dir_path)
        self.__project_script = ProjectScript("run_script_template.sh")

    def register_after_reboot_handler(self, _class: typing.Any,
                                      after_reboot_handler: AfterRebootHandler,
                                      is_reboot: bool = True) -> None:
        """Зарегистрировать обработчик, выполняемый после перезагрузки

        :param _class: Объект, который будет восстановлен после перезагрузки
        :param after_reboot_handler: Обработчик, выполняемый после перезагрузки
        :param is_reboot: Выполнить перезагрузку после регистрации
        :raises RuntimeError: Если обработчик является lambda-выражением
        """
        self.__check_func_non_lambda(after_reboot_handler)
        pickle_dump_file_path = self.__dump(_class)
        _target_class_dir_path = pathlib.Path(inspect.getfile(type(_class))).parent
        self.__startup.register_script(
            self.__get_after_reboot_script_content(pickle_dump_file_path, after_reboot_handler,
                                                   _target_class_dir_path),
            execute_mode=ExecuteMode(is_execute_once=True, is_background_executing=True, is_log_stdout=False,
                                     is_log_stderr=False))
        if is_reboot:
            Power.reboot()

    def __check_func_non_lambda(self, handler: AfterRebootHandler) -> None:
        """Проверить, что обработчик не является lambda-выражением

        :param handler: Обработчик
        :raises RuntimeError: Если обработчик является lambda-выражением
        """
        if self.__is_func_lambda(handler):
            raise RuntimeError("[RunAfterReboot] Handler cannot be a lambda expression")

    @staticmethod
    def __is_func_lambda(handler: AfterRebootHandler) -> bool:
        """Проверить, является ли обработчик lambda-выражением

        :param handler: Обработчик
        :return: ``True``, если обработчик является lambda-выражением
        """
        if isinstance(handler, types.FunctionType):
            return handler.__name__ == "<lambda>"
        return False

    def __dump(self, _class: typing.Any) -> Path:
        """Сохранить объект в pickle-файл

        :param _class: Сохраняемый объект
        :return: Путь до pickle-файла
        """
        self.__pickle_dumps_dir_path.makedirs()
        with tempfile.NamedTemporaryFile(dir=self.__pickle_dumps_dir_path, suffix=".bin", delete=False,
                                         delete_on_close=False) as file:
            pickle_dump_file_path = Path(file.name)
            pickle.dump(_class, file, protocol=pickle.HIGHEST_PROTOCOL)
        return pickle_dump_file_path

    def __get_after_reboot_script_content(self, pickle_dump_file_path: str | os.PathLike[str],
                                          after_reboot_handler: AfterRebootHandler,
                                          target_class_dir_path: str | os.PathLike[str]) -> str:
        """Сформировать командную строку запуска обработчика после перезагрузки

        :param pickle_dump_file_path: Путь до pickle-файла
        :param after_reboot_handler: Обработчик
        :param target_class_dir_path: Директория с классом объекта
        :return: Командная строка запуска обработчика
        """
        return self.__project_script.get_run_cmd_in_shell(
            f'"lib/python/startup/run_after_reboot.py" "{pickle_dump_file_path}" '
            f'"{after_reboot_handler.__name__}" "{target_class_dir_path}"')

    @staticmethod
    def run_after_reboot_handler(pickle_dump_file_path: str | os.PathLike[str], after_reboot_handler: str,
                                 target_class_dir_path: str | os.PathLike[str]) -> None:
        """Выполнить обработчик из pickle-файла

        :param pickle_dump_file_path: Путь до pickle-файла
        :param after_reboot_handler: Имя обработчика
        :param target_class_dir_path: Директория с классом объекта
        """
        pickle_dump_file_path = Path(pickle_dump_file_path)
        try:
            sys.path.append(str(target_class_dir_path))
            with open(pickle_dump_file_path, 'rb') as file:
                _class = pickle.load(file)
            getattr(_class, after_reboot_handler)()
        finally:
            pickle_dump_file_path.unlink(missing_ok=True)


if __name__ == '__main__':
    RunAfterReboot.run_after_reboot_handler(pickle_dump_file_path=sys.argv[1], after_reboot_handler=sys.argv[2],
                                            target_class_dir_path=sys.argv[3])
