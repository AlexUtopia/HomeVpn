from __future__ import annotations
import typing

from lib.python.utils import EscapeLiteral


class ShellSerializer:
    KEY_VALUE_SEPARATOR_TABLE_DEFAULT = [{"prefix": "--", "separator": "="},
                                         {"prefix": "", "separator": " "}]

    def __init__(self, quotes_for_string_value: str = '"',
                 key_value_separator_table: list[dict[str, str]] = KEY_VALUE_SEPARATOR_TABLE_DEFAULT,
                 pair_separator: str = " ",
                 escape_literal: EscapeLiteral = EscapeLiteral(), nested_serializer: ShellSerializer | None = None,
                 nested_key_value_separator: str = " ",
                 nested_escape_literal: EscapeLiteral | None = None):
        self.__quotes_for_string_value = quotes_for_string_value
        self.__key_value_separator_table = key_value_separator_table
        self.__pair_separator = pair_separator
        self.__escape_literal = escape_literal
        self.__nested_serializer = nested_serializer
        self.__nested_key_value_separator = nested_key_value_separator
        self.__nested_escape_literal = nested_escape_literal

    def serialize(self, config: typing.Any) -> str:
        result = self.__serialize_impl(config)
        if result.endswith(self.__pair_separator):
            result = result[:len(result) - len(self.__pair_separator)]
        return result

    def __serialize_impl(self, config: typing.Any) -> str:
        result = ""
        if isinstance(config, list):
            for item in config:
                result = f"{result}{self.__serialize_impl(item)}"
        elif isinstance(config, dict):
            for key, value in config.items():
                if isinstance(value, dict) or isinstance(value, list):
                    result = f"{result}{self.__serialize_nested_impl(key, value)}"
                else:
                    result = f"{result}{self.__serialize_key_value(key, value)}"
        else:
            result = f"{result}{self.__serialize_key(config)}"
        return result

    def __serialize_nested_impl(self, key: typing.Any, value: typing.Any) -> str:
        if self.__nested_serializer:
            return self.__serialize_key_value(key, self.__nested_serializer.serialize(value), is_nested=True)
        raise Exception(f"Nested serialization policy NOT FOUND: {key}: {value}")

    def __serialize_key(self, key: typing.Any) -> str:
        if isinstance(key, str) and len(key) == 0:
            return ""
        return f"{key}{self.__pair_separator}"

    def __serialize_key_value(self, key: typing.Any, value: typing.Any, is_nested: bool = False):
        separator = self.__get_nested_separator(key) if is_nested else self.__get_separator(key)
        return f"{key}{separator}{self.__serialize_value(value, is_nested)}{self.__pair_separator}"

    def __serialize_value(self, value: typing.Any, is_nested: bool = False):
        result = str(value)
        if isinstance(value, str):
            result = self.___encode_nested_literal(result) if is_nested else self.__encode_literal(result)
            result = f"{self.__quotes_for_string_value}{result}{self.__quotes_for_string_value}"
        return result

    def __get_separator(self, key: typing.Any) -> str:
        for __key_value_separator in self.__key_value_separator_table:
            if str(key).startswith(__key_value_separator["prefix"]):
                return __key_value_separator["separator"]
        return ""

    def __get_nested_separator(self, key: typing.Any) -> str:
        if not self.__nested_key_value_separator:
            return ""
        return str(self.__nested_key_value_separator)

    def __encode_literal(self, value) -> str:
        if not self.__escape_literal:
            return value
        return self.__escape_literal.encode(value)

    def ___encode_nested_literal(self, value) -> str:
        if not self.__nested_escape_literal:
            return value
        return self.__nested_escape_literal.encode(value)
