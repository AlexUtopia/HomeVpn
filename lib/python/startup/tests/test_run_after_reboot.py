"""Тесты выполнения обработчика после перезагрузки"""

import os
import pathlib
import subprocess
import tempfile
import unittest
import uuid

from lib.python.project.project_script import ProjectScript
from lib.python.shell.run_in_bash_shell_decorator import RunInBashShellDecorator
from lib.python.shell.shell import Shell
from lib.python.startup.run_after_reboot import RunAfterReboot
from lib.python.startup.startup import FileSupervisorScript, StartupBase, SupervisorScriptContent


class UnitTestRunAfterReboot(unittest.TestCase):
    """Тесты выполнения обработчика после перезагрузки"""

    ENCODING = "utf-8"

    MUTABLE_NEW_VALUE = "__value_mutable new value"

    class TestClass:
        """Тестовый класс, восстанавливаемый после перезагрузки"""

        class InnerClass:
            """Вложенный класс для проверки pickle"""

            def get_marker(self) -> int:
                """Получить тестовый маркер

                :return: Тестовый маркер
                """
                return 33

        def __init__(self, startup: StartupBase, test_file_path: str | os.PathLike[str],
                     value_for_temp_file: str) -> None:
            """Инициализировать тестовый класс

            :param startup: Механизм запуска скриптов при старте системы
            :param test_file_path: Путь до файла с результатом
            :param value_for_temp_file: Значение для записи в файл результата
            """
            self.__run_after_reboot = RunAfterReboot(startup=startup)
            self.value_str = "hello world!!! привет мир!!!"
            self.value_dict = {"key1": "value1",
                               "key2": [1, 1.2, "bbb", (UnitTestRunAfterReboot.TestClass.InnerClass().get_marker(),
                                                         UnitTestRunAfterReboot.TestClass.InnerClass())]}
            self.__value_mutable: str | None = None
            self.__test_file_path = pathlib.Path(test_file_path)
            self.__value_for_temp_file = value_for_temp_file

        def before_reboot(self) -> None:
            """Зарегистрировать обработчик и не перезагружать систему"""
            self.__value_mutable = UnitTestRunAfterReboot.MUTABLE_NEW_VALUE
            self.__run_after_reboot.register_after_reboot_handler(self, self.after_reboot, is_reboot=False)

        def after_reboot(self) -> None:
            """Записать результат выполнения обработчика в файл"""
            self.__test_file_path.write_text(data=f'{self.__value_for_temp_file} + {self.__value_mutable}',
                                             encoding=UnitTestRunAfterReboot.ENCODING)

    def test(self) -> None:
        """Проверить выполнение обработчика после перезагрузки"""
        expected_result = str(uuid.uuid4())
        supervisor_script_id = "test_id"

        with (tempfile.NamedTemporaryFile(delete_on_close=False) as test_file,
              tempfile.NamedTemporaryFile(suffix=Shell().get_script_file_extension(),
                                          delete_on_close=False) as supervisor_script_file,
              tempfile.TemporaryDirectory() as startup_script_base_dir_path):
            test_file.close()
            supervisor_script_file.close()

            test_file_path = pathlib.Path(test_file.name)
            supervisor_script_file_path = pathlib.Path(supervisor_script_file.name)

            startup = StartupBase(
                supervisor_script_id=supervisor_script_id,
                supervisor_script=FileSupervisorScript(
                    supervisor_script_id=supervisor_script_id, supervisor_script_content=SupervisorScriptContent(
                        # Покатит без переопределения win_bash под Windows/msys2 / Windows/cygwin?
                        project_script=ProjectScript(SupervisorScriptContent.RUN_SCRIPT_TEMPLATE,
                                                     win_bash=RunInBashShellDecorator.WIN_BASH_INTERNAL_CALL),
                        startup_script_base_dir_path=startup_script_base_dir_path),
                    supervisor_script_file_path=supervisor_script_file_path,
                    is_rewrite_supervisor_script=True),
                startup_script_base_dir_path=startup_script_base_dir_path)

            test_class = UnitTestRunAfterReboot.TestClass(startup=startup, test_file_path=test_file_path,
                                                          value_for_temp_file=expected_result)
            test_class.before_reboot()
            subprocess.check_call(f'"{supervisor_script_file_path}"', shell=True)
            self.assertEqual(test_file_path.read_text(encoding=self.ENCODING),
                             f'{expected_result} + {UnitTestRunAfterReboot.MUTABLE_NEW_VALUE}')
