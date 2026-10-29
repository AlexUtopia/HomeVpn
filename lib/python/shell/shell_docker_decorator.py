"""Декоратор запуска команды в docker-контейнере"""

import typing


class ShellDockerDecorator:
    """Оборачивает команду в запуск docker-контейнера

    .. note::
       Контейнер запускается без TTY и без подключения stdin
    """

    def __init__(self, docker_image: str = "ghcr.io/msys2/msys2-docker-experimental") -> None:
        """Инициализировать декоратор

        :param docker_image: Имя docker-образа
        """
        self.__docker_image = docker_image

    def __call__(self, func: typing.Callable[..., str]) -> typing.Callable[..., str]:
        """Обернуть функцию, возвращающую команду, в запуск docker-контейнера

        :param func: Функция, возвращающая команду
        :return: Обёрнутая функция
        """

        def __decorator_func(*args: typing.Any, **kwargs: typing.Any) -> str:
            cmd_line = func(*args, **kwargs)
            return f'docker run "{self.__docker_image}" {cmd_line}'

        return __decorator_func
