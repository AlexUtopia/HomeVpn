"""Типы данных проекта: JSON, пути, файлы конфигурации."""

from .json import JsonType
from .path import Path
from .text_writer import TextConfigWriter, JsonConfigWriter
from .text_reader import TextConfigReader, JsonConfigReader

__all__ = ["JsonConfigReader",
           "JsonConfigWriter",
           "JsonType",
           "Path",
           "TextConfigReader",
           "TextConfigWriter"]
