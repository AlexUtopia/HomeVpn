"""Тесты базового класса моделей с табличным описанием полей."""

import json
import re
import typing
import unittest

from lib.python.utils import BaseParser, String, UInt8, UInt8Hex


class NestedParser(BaseParser):
    """Вложенная модель для проверки рекурсивной сериализации"""

    __TABLE: typing.ClassVar[dict[str, typing.Any]] = {"value": {"type": UInt8}}

    def __init__(self, source: typing.Any = None) -> None:
        """Создать модель

        :param source: Источник значений (модель или словарь)
        """
        super().__init__(NestedParser.__TABLE)
        if source is not None:
            self.copy_if(source)


class ParserModel(BaseParser):
    """Модель, покрывающая все варианты метаданных поля"""

    __TABLE: typing.ClassVar[dict[str, typing.Any]] = {
        "name": {"type": String},
        "count": {"type": UInt8},
        "hex": {"type": UInt8Hex},
        "optional": {"type": UInt8, "default": None},
        "explicit": {"type": UInt8, "default": 7},
        "nested": {"type": NestedParser}}

    def __init__(self, source: typing.Any = None) -> None:
        """Создать модель

        :param source: Источник значений (модель или словарь)
        """
        super().__init__(ParserModel.__TABLE)
        if source is not None and not self.copy_if(source):
            raise ValueError(f"Unsupported source: {source}")


class BrokenParser(BaseParser):
    """Модель с метаданными поля без типа"""

    def __init__(self) -> None:
        """Создать модель с некорректной таблицей полей"""
        super().__init__({"broken": {}})


class UnitTest_BaseParser(unittest.TestCase):  # pylint: disable=invalid-name
    """Проверка заполнения, разбора и сериализации полей"""

    def test_defaults(self) -> None:
        """Поля без default получают <тип>(), поля с default — указанное значение"""
        model = ParserModel()

        self.assertEqual(model["name"], "")
        self.assertEqual(model["count"], 0)
        self.assertEqual(model["hex"], 0)
        self.assertIsNone(model["optional"])
        self.assertEqual(model["explicit"], 7)
        self.assertIsInstance(model["count"], UInt8)

    def test_setitem_converts_value(self) -> None:
        """Присвоение преобразует строку в тип поля"""
        model = ParserModel()

        model["count"] = "5"
        model["hex"] = "0a"

        self.assertIsInstance(model["count"], UInt8)
        self.assertEqual(model["count"], 5)
        self.assertEqual(model["hex"], 10)
        self.assertEqual(str(model["hex"]), "0a")

    def test_setitem_none(self) -> None:
        """None сохраняется без преобразования типа"""
        model = ParserModel()

        model["optional"] = None
        model["count"] = None

        self.assertIsNone(model["optional"])
        self.assertIsNone(model["count"])

    def test_unknown_field(self) -> None:
        """Неизвестное поле приводит к KeyError"""
        model = ParserModel()

        with self.assertRaises(KeyError):
            model["unknown"] = 1

    def test_metadata_without_type(self) -> None:
        """Метаданные без типа поля приводят к ValueError"""
        with self.assertRaises(ValueError):
            BrokenParser()

    def test_init_fields(self) -> None:
        """Поля заполняются из строки по именованным группам регулярного выражения"""
        model = ParserModel()
        regex = re.compile(fr"count=(?P<count>{UInt8.get_regex()}),hex=(?P<hex>{UInt8Hex.get_regex()})")

        self.assertTrue(model.init_fields(regex, "count=42,hex=1f"))
        self.assertEqual(model["count"], 42)
        self.assertEqual(model["hex"], 0x1F)

    def test_init_fields_rejects_non_string_and_mismatch(self) -> None:
        """Не строка и несовпадение с выражением дают False"""
        model = ParserModel()
        regex = re.compile(fr"count=(?P<count>{UInt8.get_regex()})")

        self.assertFalse(model.init_fields(regex, 42))
        self.assertFalse(model.init_fields(regex, "hex=1f"))
        self.assertEqual(model["count"], 0)

    def test_copy_if(self) -> None:
        """Копирование из словаря и модели, отказ для чужого типа"""
        model = ParserModel({"count": "5", "nested": {"value": "9"}})

        self.assertEqual(model["count"], 5)
        self.assertEqual(model["nested"]["value"], 9)
        self.assertEqual(model["explicit"], 7)  # default не потерян
        self.assertEqual(model["name"], "")  # отсутствующее поле заполнено <тип>()

        copy = ParserModel(model)
        self.assertEqual(copy.get_fields_as_dict(), model.get_fields_as_dict())
        self.assertFalse(model.copy_if(17))

    def test_get_fields_as_dict(self) -> None:
        """Словарь полей содержит вложенные модели как словари"""
        model = ParserModel({"count": "5", "nested": {"value": "9"}})

        self.assertEqual(model.get_fields_as_dict(),
                         {"name": "",
                          "count": 5,
                          "hex": 0,
                          "optional": None,
                          "explicit": 7,
                          "nested": {"value": 9}})

    def test_str_and_repr(self) -> None:
        """str() и repr() дают одинаковый JSON"""
        model = ParserModel({"count": "5"})

        self.assertEqual(json.loads(str(model))["count"], 5)
        self.assertEqual(repr(model), str(model))
        self.assertEqual(str(model), json.dumps(model.get_fields_as_dict()))

    def test_get_regex_for(self) -> None:
        """Регулярное выражение поля: с группой, без группы и для отсутствующего поля"""
        model = ParserModel()

        self.assertEqual(model.get_regex_for("count"), fr"(?P<count>{UInt8.get_regex()})")
        self.assertEqual(model.get_regex_for("count", is_capture=False), UInt8.get_regex())
        self.assertEqual(model.get_regex_for("unknown"), "")
