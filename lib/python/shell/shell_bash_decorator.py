"""Декоратор запуска команды в bash"""

import typing

from lib.python.utils.escape_literal import EscapeLiteral


class ShellBashDecorator:
    """Оборачивает команду в вызов bash

    .. note::
       Команда должна быть одной строкой: переводы строк не поддерживаются
    """

    __ENCODE_TABLE_FOR_REDUCE_NEW_LINE_ESCAPING: list[tuple[str, str]] = [("\\\r\n", ""), ("\\\n\r", ""),
                                                                          ("\\\n", ""), ("\\\r", "")]

    __ENCODE_TABLE: list[tuple[str, str]] = [("\\", "\\\\"), ("$", "\\$"), ("\"", "\\\"")]

    def __call__(self, func: typing.Callable[..., str]) -> typing.Callable[..., str]:
        """Обернуть функцию, возвращающую команду, в вызов bash

        :param func: Функция, возвращающая команду
        :return: Обёрнутая функция
        """

        def __decorator_func(*args: typing.Any, **kwargs: typing.Any) -> str:
            cmd_line = func(*args, **kwargs)
            cmd_line = self.full_escape_cmd_line(cmd_line)
            self.__check_cmd_line(cmd_line)
            return f'bash -l -c "{cmd_line}"'

        return __decorator_func

    def full_escape_cmd_line(self, cmd_line: str) -> str:
        """Экранировать команду для bash

        :param cmd_line: Команда
        :return: Экранированная команда
        """
        return EscapeLiteral(
            encode_table=self.__ENCODE_TABLE_FOR_REDUCE_NEW_LINE_ESCAPING + self.__ENCODE_TABLE).encode(cmd_line)

    def escape_cmd_line_for_win(self, cmd_line: str) -> str:
        """Экранировать команду для Windows

        :param cmd_line: Команда
        :return: Экранированная команда
        """
        return EscapeLiteral(encode_table=[("\\", "\\\\")]).encode(cmd_line)

    def __check_cmd_line(self, cmd_line: str) -> None:
        """Проверить, что команда является одной строкой

        :param cmd_line: Команда
        :raises ValueError: Если команда содержит перевод строки
        """
        if "\n" in cmd_line or "\r" in cmd_line:
            raise ValueError("[bash] only single string command available")
