import inspect
import os
import pathlib
import pickle
import sys
import tempfile
import types
import typing

from lib.python.power import Power
from lib.python.project import ProjectScript
from lib.python.startup import Startup, ExecuteMode
from lib.python.types import Path


class RunAfterReboot:
    def __init__(self, startup=Startup(),
                 pickle_dumps_dir_path: str | os.PathLike[str] = Path("data/execute_after_reboot")):
        self.__startup = startup
        self.__pickle_dumps_dir_path = Path(pickle_dumps_dir_path)
        self.__project_script = ProjectScript("run_script_template.sh")

    def register_after_reboot_handler(self, _class: typing.Any,
                                      after_reboot_handler: typing.Callable[[], None],
                                      is_reboot: bool = True):
        self.__check_func_non_lambda(after_reboot_handler)
        pickle_dump_file_path = self.__dump(_class)
        _target_class_dir_path = pathlib.Path(inspect.getfile(type(_class))).parent
        self.__startup.register_script(
            self.__get_after_reboot_script_content(pickle_dump_file_path, after_reboot_handler, _target_class_dir_path),
            execute_mode=ExecuteMode(is_execute_once=True, is_background_executing=True, is_log_stdout=False,
                                     is_log_stderr=False))
        if is_reboot:
            Power.reboot()

    def __check_func_non_lambda(self, handler: typing.Callable[[], None]) -> None:
        if self.__is_func_lambda(handler):
            raise Exception("[RunAfterReboot] Handler cannot be a lambda expression")

    def __is_func_lambda(self, handler: typing.Callable[[], None]) -> bool:
        is_func = isinstance(handler, types.FunctionType)
        return (handler.__name__ == "<lambda>") if is_func else False

    def __dump(self, _class: typing.Any) -> Path:
        self.__pickle_dumps_dir_path.makedirs()
        pickle_dump_file_path = None
        with tempfile.NamedTemporaryFile(dir=self.__pickle_dumps_dir_path, suffix=".bin", delete=False,
                                         delete_on_close=False) as file:
            pickle_dump_file_path = Path(file.name)
            pickle.dump(_class, file, protocol=pickle.HIGHEST_PROTOCOL)
        return pickle_dump_file_path

    def __get_after_reboot_script_content(self, pickle_dump_file_path: str | os.PathLike[str],
                                          after_reboot_handler: typing.Callable[[], None],
                                          target_class_dir_path: str | os.PathLike[str]) -> str:
        return self.__project_script.get_run_cmd_in_shell(
            f'"lib/python/startup/run_after_reboot.py" "{pickle_dump_file_path}" "{after_reboot_handler.__name__}" "{target_class_dir_path}"')

    @staticmethod
    def run_after_reboot_handler(pickle_dump_file_path: str | os.PathLike[str], after_reboot_handler: str,
                                 target_class_dir_path: str | os.PathLike[str]):
        pickle_dump_file_path = Path(pickle_dump_file_path)
        try:
            sys.path.append(target_class_dir_path)
            _class = None
            with open(pickle_dump_file_path, 'rb') as f:
                _class = pickle.load(f)
            getattr(_class, after_reboot_handler)()
        finally:
            pickle_dump_file_path.unlink(missing_ok=True)


if __name__ == '__main__':
    RunAfterReboot.run_after_reboot_handler(pickle_dump_file_path=sys.argv[1], after_reboot_handler=sys.argv[2],
                                            target_class_dir_path=sys.argv[3])
