"""Утилиты работы с подклассами."""

import typing


def get_all_subclasses(cls: type[typing.Any]) -> list[type[typing.Any]]:
    """Получить все подклассы класса (рекурсивно)

    :param cls: Класс
    :return: Список подклассов в порядке, обратном порядку обнаружения
    """
    result: list[type[typing.Any]] = list(cls.__subclasses__())
    for sub_cls in cls.__subclasses__():
        for sub_sub_cls in get_all_subclasses(sub_cls):
            if sub_sub_cls not in result:
                result.append(sub_sub_cls)
    result.reverse()
    return result
