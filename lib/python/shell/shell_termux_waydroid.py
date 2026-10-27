"""Декоратор запуска команды в termux (bash) внутри waydroid"""

import typing

from lib.python.types.path import Path

from .shell_bash_decorator import ShellBashDecorator


class ShellTermuxWaydroid:
    """Оборачивает команду в запуск скрипта termux внутри waydroid

    .. note::
       Запускается ``scripts/waydroid-termux-shell-run-command.sh``
    """

    def __call__(self, func: typing.Callable[..., str]) -> typing.Callable[..., str]:
        """Обернуть функцию, возвращающую команду, в запуск скрипта waydroid

        :param func: Функция, возвращающая команду
        :return: Обёрнутая функция
        """

        def __decorator_func(*args: typing.Any, **kwargs: typing.Any) -> str:
            cmd_line = func(*args, **kwargs)
            cmd_line = ShellBashDecorator().full_escape_cmd_line(cmd_line)
            script_path = self.get_waydroid_termux_shell_run_command_script_path()
            return f'WAYDROID_TRY_RUN_COMMAND_OVER_SSH= "{script_path}" "{cmd_line}"'

        return __decorator_func

    def get_waydroid_termux_shell_run_command_script_path(self) -> Path:
        """Получить путь до скрипта запуска команды в termux внутри waydroid

        :return: Путь до скрипта
        """
        return Path("scripts/waydroid-termux-shell-run-command.sh")
