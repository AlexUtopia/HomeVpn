import json
import os

from lib.python.types import JsonType
from lib.python.types import Path

from .text_writer import JsonConfigWriter


class TextConfigReader:
    def __init__(self, config_file_path: str | os.PathLike[str], encoding: str = "utf-8"):
        self.__config_file_path = Path(config_file_path)
        self.__encoding = str(encoding)

    def __str__(self):
        return str(self.__config_file_path)

    def __repr__(self):
        return self.__str__()

    def get(self) -> str:
        return self.__load_from_config()

    def exists(self) -> bool:
        return self.__config_file_path.exists()

    def __load_from_config(self) -> str:
        result = ""
        with open(self.__config_file_path, mode="rt", encoding=self.__encoding) as config_file:
            result += str(config_file.read())
        return result


class JsonConfigReader:
    def __init__(self, config_file_path: str | os.PathLike[str], encoding: str = "utf-8"):
        self.__text_config_reader = TextConfigReader(config_file_path, encoding)
        self.__json_config_writer = JsonConfigWriter(config_file_path, encoding)

    def get(self) -> JsonType:
        return json.loads(self.__text_config_reader.get())

    def get_or_create_if_non_exists(self, default_content_if_create: JsonType = dict()) -> str:
        if not self.__text_config_reader.exists():
            self.__json_config_writer.set(default_content_if_create)
        return self.get()