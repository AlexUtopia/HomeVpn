"""Базовый класс моделей с табличным описанием полей."""

import json
import re
import types
import typing


# Класс, экземпляры которого можно присвоить полю: должен уметь разобрать строку и отдать регулярку
FieldType = type[typing.Any]
FieldValue = typing.Any
# {"type": FieldType, "default": FieldValue}
FieldMetadata = dict[str, typing.Any]

# Признак того, что значение по умолчанию у поля не задано
_NO_DEFAULT = object()

_FIELD_TABLE_CACHE: dict[type, dict[str, FieldMetadata]] = {}


class Field:
    """Метаданные поля модели для ``typing.Annotated``

    ``Field()`` — значение по умолчанию не задано, полю будет присвоено
    ``<тип>()``. ``Field(default=None)`` — полю будет присвоено ``None``.

    .. note::
       Метаданные читаются только из аннотаций самого класса и его предков,
       унаследованных от :class:`BaseParser`.
    """

    def __init__(self, default: FieldValue = _NO_DEFAULT) -> None:
        """Создать метаданные поля

        :param default: Значение по умолчанию; если не задано, используется ``<тип>()``
        """
        self.default = default

    @property
    def has_default(self) -> bool:
        """Признак явно заданного значения по умолчанию"""
        return self.default is not _NO_DEFAULT


def _get_annotations(cls: type) -> dict[str, typing.Any]:
    """Получить аннотации, объявленные непосредственно в классе

    :param cls: Класс модели
    :return: Словарь ``{имя: аннотация}``
    """
    annotations: dict[str, typing.Any] = dict(cls.__dict__.get("__annotations__", {}))
    if any(isinstance(annotation, str) for annotation in annotations.values()):
        return dict(typing.get_type_hints(cls, include_extras=True))
    return annotations


def _get_parser_type(annotation: typing.Any) -> FieldType:
    """Получить тип-разборщик из аннотации поля

    :param annotation: Аннотация поля, например ``UInt8 | None``
    :return: Тип, у которого берутся ``get_regex()`` и конструктор
    """
    union_args = [argument for argument in typing.get_args(annotation) if argument is not types.NoneType]
    if len(union_args) == 1:
        return typing.cast(FieldType, union_args[0])
    return typing.cast(FieldType, annotation)


def _get_field_metadata(annotation: typing.Any) -> FieldMetadata | None:
    """Получить метаданные поля из ``typing.Annotated``

    :param annotation: Аннотация поля
    :return: Метаданные поля или ``None``, если аннотация не описывает поле
    """
    if typing.get_origin(annotation) is not typing.Annotated:
        return None

    annotation_args = typing.get_args(annotation)
    field = next((argument for argument in annotation_args[1:] if isinstance(argument, Field)), None)
    if field is None:
        return None

    metadata: FieldMetadata = {"type": _get_parser_type(annotation_args[0])}
    if field.has_default:
        metadata["default"] = field.default
    return metadata


def _get_field_table(cls: type) -> dict[str, FieldMetadata]:
    """Собрать таблицу полей модели из аннотаций ``typing.Annotated``

    Поля предков добавляются первыми, поля наследника могут их переопределить.
    Результат кешируется по классу.

    :param cls: Класс модели
    :return: Таблица полей в формате :class:`BaseParser`
    """
    cached = _FIELD_TABLE_CACHE.get(cls)
    if cached is not None:
        return cached

    result: dict[str, FieldMetadata] = {}
    for base in reversed(cls.__mro__):
        for field_name, annotation in _get_annotations(base).items():
            metadata = _get_field_metadata(annotation)
            if metadata is not None:
                result[field_name] = metadata
    _FIELD_TABLE_CACHE[cls] = result
    return result


class BaseParser:
    """Модель с динамическим набором полей

    Поля описываются таблицей ``{имя: {"type": <тип>, "default": <значение>}}``
    либо аннотациями ``typing.Annotated``::

        class Model(BaseParser):
            name: typing.Annotated[String, Field()]
            iommu_group: typing.Annotated[UInt8 | None, Field(default=None)]

    Ключ ``default`` необязателен: если он отсутствует, полю присваивается
    значение ``<тип>()``, если присутствует — указанное значение (в том числе
    ``None``).

    .. note::
       Тип поля должен предоставлять статический метод ``get_regex()`` и
       конструктор, принимающий строковое представление значения.
    """

    def __init__(self, table: typing.Mapping[str, FieldMetadata] | None = None) -> None:
        """Создать модель и заполнить поля значениями по умолчанию

        :param table: Таблица полей модели; при ``None`` собирается из аннотаций
                      ``typing.Annotated`` самого класса и его предков
        """
        self.__table = dict(table) if table is not None else _get_field_table(type(self))
        self.init_fields_default()

    def __setitem__(self, key: str, value: FieldValue) -> None:
        """Присвоить значение полю по имени

        :param key: Имя поля
        :param value: Значение поля; ``None`` сохраняется без преобразования типа
        :raises KeyError: Поле отсутствует в таблице модели
        """
        metadata = self.__table.get(key)
        if metadata is None:
            raise KeyError(f"[{type(self).__name__}] Unknown field: {key}")

        field_type = self.__get_field_type(metadata)

        if value is None:
            setattr(self, key, value)
            return

        setattr(self, key, field_type(value))

    def __getitem__(self, key: str) -> FieldValue:
        """Получить значение поля по имени

        :param key: Имя поля
        :return: Значение поля
        """
        return getattr(self, key)

    def __str__(self) -> str:
        """Сериализовать модель в JSON

        :return: JSON-представление полей модели
        """
        return json.dumps(self.get_fields_as_dict())

    def __repr__(self) -> str:
        """Сериализовать модель в JSON

        :return: JSON-представление полей модели
        """
        return self.__str__()

    def get_fields_as_dict(self) -> dict[str, FieldValue]:
        """Получить поля модели в виде словаря

        :return: Словарь ``{имя поля: значение}``; вложенные модели раскрываются рекурсивно
        """
        result: dict[str, FieldValue] = {}
        for field_name in self.__table:
            field_value = self[field_name]
            if isinstance(field_value, BaseParser):
                result[field_name] = field_value.get_fields_as_dict()
            else:
                result[field_name] = field_value
        return result

    def init_fields_default(self) -> None:
        """Заполнить поля значениями по умолчанию

        Использует ``default`` из таблицы поля, а при его отсутствии —
        результат вызова ``<тип>()``.
        """
        for field_name, metadata in self.__table.items():
            self.__set_field_default(field_name, metadata)

    def init_fields(self, re_object: re.Pattern[str], value_as_str: FieldValue) -> bool:
        """Заполнить поля из строки по регулярному выражению

        Имена именованных групп регулярного выражения должны совпадать с
        именами полей модели.

        :param re_object: Скомпилированное регулярное выражение
        :param value_as_str: Строка для разбора
        :return: ``True`` — строка разобрана, ``False`` — значение не является строкой
                 или не соответствует выражению
        """
        if not isinstance(value_as_str, str):
            return False

        match = re_object.search(value_as_str)
        if match is None:
            return False

        for field_name, value in match.groupdict().items():
            if value is not None:
                self[field_name] = value
        return True

    def copy_if(self, other: FieldValue) -> bool:
        """Скопировать поля из другой модели или словаря

        Отсутствующие в источнике поля заполняются значением по умолчанию:
        ``default`` из метаданных поля, а при его отсутствии — ``<тип>()``.

        :param other: Модель того же типа (или его предка) либо словарь значений
        :return: ``True`` — источник подходит и поля скопированы, ``False`` — источник не подходит
        """
        if not (isinstance(other, (type(self), dict)) or isinstance(self, type(other))):
            return False

        other_dict = other if isinstance(other, dict) else other.get_fields_as_dict()
        for field_name, metadata in self.__table.items():
            if field_name in other_dict:
                self[field_name] = other[field_name]
            else:
                self.__set_field_default(field_name, metadata)
        return True

    def get_regex_for(self, field_name: str, is_capture: bool = True) -> str:
        """Получить регулярное выражение поля

        :param field_name: Имя поля
        :param is_capture: Обернуть выражение в именованную группу с именем поля
        :return: Регулярное выражение поля или пустая строка, если поле отсутствует
        """
        metadata = self.__table.get(field_name)
        if metadata is None:
            return ""

        field_type = self.__get_field_type(metadata)
        if is_capture:
            return f"(?P<{field_name}>{field_type.get_regex()})"
        return str(field_type.get_regex())

    def __set_field_default(self, field_name: str, metadata: FieldMetadata) -> None:
        """Присвоить полю значение по умолчанию

        :param field_name: Имя поля
        :param metadata: Метаданные поля
        """
        if "default" in metadata:
            self[field_name] = metadata["default"]
            return
        setattr(self, field_name, self.__get_field_type(metadata)())

    @staticmethod
    def __get_field_type(metadata: FieldMetadata) -> FieldType:
        """Получить тип поля из метаданных

        :param metadata: Метаданные поля
        :return: Тип поля
        :raises ValueError: В метаданных отсутствует тип поля
        """
        field_type = metadata.get("type")
        if field_type is None:
            raise ValueError(f"Field metadata has no type: {metadata}")
        return typing.cast(FieldType, field_type)
