"""Утилиты декорирования"""

import typing


def apply_decorators(
        decorators_list: typing.Sequence[typing.Callable[..., typing.Any]]
) -> typing.Callable[..., typing.Any]:
    """Применить список декораторов к функции

    :param decorators_list: Последовательность декораторов
    :return: Декоратор, применяющий список декораторов в обратном порядке
    """

    def decorator(func: typing.Callable[..., typing.Any]) -> typing.Callable[..., typing.Any]:
        for decorator_item in reversed(decorators_list):
            func = decorator_item(func)
        return func

    return decorator
