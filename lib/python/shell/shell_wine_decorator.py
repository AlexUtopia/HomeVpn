"""Декоратор запуска команды через wine"""

import os
import pathlib
import typing

from lib.python.system.current_os import CurrentOs


class ShellWineDecorator:
    """Оборачивает команду в вызов wine

    .. note::
       WineHQ запускается из-под bash, рекомендуется применять совместно с ShellCmdDecorator
    .. seealso::
       https://askubuntu.com/questions/880832/what-is-the-difference-between-wine-and-wine64
       https://unix.stackexchange.com/questions/801401/wine-cmd-automatically-escapes-quotes-adds-backslash
    """

    @staticmethod
    def get_wine_executable_path() -> pathlib.Path:
        """Получить путь до исполняемого файла wine

        :return: Путь до исполняемого файла wine
        :raises RuntimeError: Если wine недоступен
        """
        if CurrentOs.is_linux():
            wine_default = pathlib.Path("wine")
            wine_stable = pathlib.Path("/opt/wine-stable/bin/wine")
            if wine_stable.exists():
                return wine_stable
            return wine_default
        if CurrentOs.is_termux():
            return pathlib.Path("wine-stable")
        raise RuntimeError("[wine] Wine is not available")

    def __init__(self, wine_path: str | os.PathLike[str] | None = None,
                 is_crutch_for_msys2_over_wine: bool = False) -> None:
        """Инициализировать декоратор

        :param wine_path: Путь до исполняемого файла wine; если не задан, определяется автоматически
        :param is_crutch_for_msys2_over_wine: Применить обход для MSYS2 поверх wine
        """
        self.__wine_path = pathlib.Path(wine_path) if wine_path else self.get_wine_executable_path()
        self.__is_crutch_for_msys2_over_wine = is_crutch_for_msys2_over_wine

    def __call__(self, func: typing.Callable[..., str]) -> typing.Callable[..., str]:
        """Обернуть функцию, возвращающую команду, в вызов wine

        :param func: Функция, возвращающая команду
        :return: Обёрнутая функция
        """

        def __decorator_func(*args: typing.Any, **kwargs: typing.Any) -> str:
            cmd_line = func(*args, **kwargs)
            return f'{self.__crutch_for_msys2_over_wine()}WINEDEBUG=-all && "{self.__wine_path}" {cmd_line}'

        return __decorator_func

    def __crutch_for_msys2_over_wine(self) -> str:
        """Получить обход проблемы MSYS2 поверх wine

        :return: Префикс команды для обхода проблемы
        """
        if not self.__is_crutch_for_msys2_over_wine:
            return ""
        return 'sed -i \'s/delims=,;=	 "/delims=,;= "/g\' ~/.wine/drive_c/msys64/msys2_shell.cmd && '
