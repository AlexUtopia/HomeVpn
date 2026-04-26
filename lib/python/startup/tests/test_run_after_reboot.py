import os
import pathlib
import subprocess
import tempfile
import unittest
import uuid

from lib.python.project import ProjectScript
from lib.python.shell import RunInBashShellDecorator, Shell
from lib.python.startup import RunAfterReboot
from lib.python.startup import StartupBase, SupervisorScriptContent, FileSupervisorScript


class UnitTest_RunAfterReboot(unittest.TestCase):
    ENCODING = "utf-8"

    MUTABLE_NEW_VALUE = "__value_mutable new value"

    class TestClass:
        class InnerClass:
            pass

        def __init__(self, startup, test_file_path: str | os.PathLike[str], value_for_temp_file: str):
            self.__run_after_reboot = RunAfterReboot(startup=startup)
            self.__value_str = "hello world!!! привет мир!!!"
            self.__value_dict = {"key1": "value1",
                                 "key2": [1, 1.2, "bbb", (33, UnitTest_RunAfterReboot.TestClass.InnerClass())]}
            self.__value_mutable = None
            self.__test_file_path = pathlib.Path(test_file_path)
            self.__value_for_temp_file = value_for_temp_file

        def before_reboot(self):
            self.__value_mutable = UnitTest_RunAfterReboot.MUTABLE_NEW_VALUE
            self.__run_after_reboot.register_after_reboot_handler(self, self.after_reboot, is_reboot=False)

        def after_reboot(self) -> None:
            self.__test_file_path.write_text(data=f'{self.__value_for_temp_file} + {self.__value_mutable}',
                                             encoding=UnitTest_RunAfterReboot.ENCODING)

    def test(self):
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
                        # fixme utopia Покатит без переопределения win_bash под Windows/msys2 / Windows/cygwin?
                        project_script=ProjectScript(SupervisorScriptContent.RUN_SCRIPT_TEMPLATE,
                                                     win_bash=RunInBashShellDecorator.WIN_BASH_INTERNAL_CALL),
                        startup_script_base_dir_path=startup_script_base_dir_path),
                    supervisor_script_file_path=supervisor_script_file_path,
                    is_rewrite_supervisor_script=True),
                startup_script_base_dir_path=startup_script_base_dir_path)

            test_class = UnitTest_RunAfterReboot.TestClass(startup=startup, test_file_path=test_file_path,
                                                           value_for_temp_file=expected_result)
            test_class.before_reboot()
            subprocess.check_call(f'"{supervisor_script_file_path}"', shell=True)
            self.assertEqual(test_file_path.read_text(encoding=self.ENCODING),
                             f'{expected_result} + {UnitTest_RunAfterReboot.MUTABLE_NEW_VALUE}')
