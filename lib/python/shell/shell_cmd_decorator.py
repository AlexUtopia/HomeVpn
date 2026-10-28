"""Декоратор запуска команды в cmd.exe"""

import typing

from lib.python.utils.escape_literal import EscapeLiteral


class ShellCmdDecorator:
    """Оборачивает команду в вызов cmd.exe

    .. note::
       Требуется доработка: экранирование спецсимволов cmd.exe
    .. seealso::
       https://ss64.com/nt/syntax-esc.html
       https://stackoverflow.com/questions/10296162/escaping-special-characters-in-cmd
    """

    __ENCODE_TABLE_FOR_REDUCE_NEW_LINE_ESCAPING: list[tuple[str, str]] = [("^\r\n", ""), ("^\n\r", ""),
                                                                          ("^\n", ""), ("^\r", "")]

    __ENCODE_TABLE: list[tuple[str, str]] = [("^", "^^"), ("&", "^&"), ("%", "%%"), ("|", "^|"), ("\"", "\"\"")]

    def __init__(self, cmd_path: str = r'%COMSPEC%') -> None:
        """Инициализировать декоратор

        :param cmd_path: Путь до исполняемого файла cmd.exe; раскрывается при выполнении командной строки
        """
        self.__cmd_path = cmd_path

    def __call__(self, func: typing.Callable[..., str]) -> typing.Callable[..., str]:
        """Обернуть функцию, возвращающую команду, в вызов cmd.exe

        :param func: Функция, возвращающая команду
        :return: Обёрнутая функция
        """

        def __decorator_func(*args: typing.Any, **kwargs: typing.Any) -> str:
            cmd_line = func(*args, **kwargs)
            cmd_line = self.full_escape_cmd_line(cmd_line)
            self.__check_cmd_line(cmd_line)
            return f'"{self.__cmd_path}" /q /c "{cmd_line}"'

        return __decorator_func

    def full_escape_cmd_line(self, cmd_line: str) -> str:
        """Экранировать команду для cmd.exe

        :param cmd_line: Команда
        :return: Экранированная команда
        """
        return EscapeLiteral(
            encode_table=self.__ENCODE_TABLE_FOR_REDUCE_NEW_LINE_ESCAPING + self.__ENCODE_TABLE).encode(cmd_line)

    def __check_cmd_line(self, cmd_line: str) -> None:
        """Проверить, что команда является одной строкой

        :param cmd_line: Команда
        :raises ValueError: Если команда содержит перевод строки
        """
        if "\n" in cmd_line or "\r" in cmd_line:
            raise ValueError("[cmd] only single string command available")
