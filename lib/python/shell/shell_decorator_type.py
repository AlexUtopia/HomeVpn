"""Типы декораторов команд"""

import typing

ShellCommand = typing.Callable[..., str]
ShellDecorator = typing.Callable[[ShellCommand], ShellCommand]
