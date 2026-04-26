import json


# fixme utopia Перевести BaseParser на прогон по __dict__ и from typing import Annotated
class BaseParser:
    def __init__(self, table):
        self.__table = table
        self.init_fields_default()

    def __setitem__(self, key, value):
        metadata = self.__table.get(key)
        if metadata is None:
            return

        field_type = self.__get_field_type(metadata)
        if field_type is None:
            return

        if value is None:
            setattr(self, key, value)
            return

        setattr(self, key, field_type(value))

    def __getitem__(self, key):
        return getattr(self, key)

    def __str__(self):
        return json.dumps(self.get_fields_as_dict())

    def __repr__(self):
        return self.__str__()

    def get_fields_as_dict(self):
        result = dict()
        for field_name, metadata in self.__table.items():
            field_value = self[field_name]
            if isinstance(field_value, BaseParser):
                result[field_name] = field_value.get_fields_as_dict()
            else:
                result[field_name] = field_value
        return result

    def init_fields_default(self):
        for field_name, metadata in self.__table.items():
            if "default" in metadata:
                self[field_name] = metadata.get("default")
            else:
                setattr(self, field_name, self.__get_field_type(metadata)())

    def init_fields(self, re_object, value_as_str):
        if not isinstance(value_as_str, str):
            return False

        match = re_object.search(str(value_as_str))
        if match is None:
            return False

        for field_name, value in match.groupdict().items():
            if value is not None:
                self[field_name] = value
        return True

    def copy_if(self, other):
        if isinstance(other, type(self)) or isinstance(self, type(other)) or isinstance(other, dict):
            other_dict = other if isinstance(other, dict) else other.get_fields_as_dict()
            for field_name, metadata in self.__table.items():
                if field_name in other_dict:
                    self[field_name] = other[field_name]
                else:
                    setattr(self, field_name, self.__get_field_type(metadata)())
            return True
        else:
            return False

    # @staticmethod
    # def from_string(model):
    #     Pci.from_json(json.loads(model))
    #
    # @staticmethod
    # def from_json(model):
    #     result = Pci()
    #     for key, value in model.items():
    #         result[key] = value
    #     return Pci.__build(result)

    def get_regex_for(self, field_name, is_capture=True):
        metadata = self.__table.get(field_name)
        if metadata is None:
            return ""

        field_type = self.__get_field_type(metadata)
        if field_type is None:
            return ""

        if is_capture:
            return f"(?P<{field_name}>{field_type.get_regex()})"
        else:
            return field_type.get_regex()

    def __get_field_type(self, metadata):
        return metadata.get("type")
