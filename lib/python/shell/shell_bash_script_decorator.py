"""Декоратор запуска команды через временный shell-скрипт"""

import typing

from lib.python.utils.decorator import apply_decorators

from .shell_bash_decorator import ShellBashDecorator
from .shell_decorator_type import ShellCommand, ShellDecorator


class ShellBashScriptDecorator:
    """Оборачивает команду в запуск временного shell-скрипта

    .. note::
       Для wine директория /tmp не годится, т.к. монтируется в wine в режиме noexec
    """

    TEMP_PATH = "TEMP_PATH"

    def __init__(self, call_wrapper_decorator_list: typing.Sequence[ShellDecorator],
                 temp_script_file_extension: str = "") -> None:
        """Инициализировать декоратор

        :param call_wrapper_decorator_list: Список декораторов вызова скрипта
        :param temp_script_file_extension: Расширение временного файла скрипта
        """
        self.__call_wrapper_decorator_list = call_wrapper_decorator_list
        self.__temp_script_file_extension = temp_script_file_extension
        self.__script_file_path = f'${self.TEMP_PATH}'

    def __call__(self, func: ShellCommand) -> ShellCommand:
        """Обернуть функцию, возвращающую команду, в запуск временного скрипта

        :param func: Функция, возвращающая команду
        :return: Обёрнутая функция
        """

        def __wrapper() -> str:
            return self.__script_file_path

        call_script_cmd_line = apply_decorators(self.__call_wrapper_decorator_list)(__wrapper)()

        def __decorator_func(*args: typing.Any, **kwargs: typing.Any) -> str:
            cmd_line = func(*args, **kwargs)
            cmd_line = ShellBashDecorator().full_escape_cmd_line(cmd_line)
            return f'{self.TEMP_PATH}="$(mktemp ~/XXXXXXXXX{self.__temp_script_file_extension})"' \
                   f' && trap "rm -f \"{self.__script_file_path}\"" EXIT' \
                   f' && echo "{cmd_line}" > "{self.__script_file_path}"' \
                   f' && chmod +x "{self.__script_file_path}"' \
                   f' && {call_script_cmd_line}'

        return __decorator_func
