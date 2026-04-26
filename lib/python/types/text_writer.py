import json
import os
import typing

from lib.python.types import JsonType
from lib.python.types import Path


class TextConfigWriter:
    def __init__(self, config_file_path: str | os.PathLike[str], encoding: str = "utf-8",
                 last_backup_file_path: str | os.PathLike[str] | None = None):
        self.__config_file_path = Path(config_file_path)
        self.__encoding = str(encoding)
        self.__last_backup_file_path: Path | None = Path(last_backup_file_path) if last_backup_file_path else None

    def __str__(self):
        return str(self.__config_file_path)

    def __repr__(self):
        return self.__str__()

    def set(self, data: typing.Any, set_executable: bool = False) -> Path:
        self.__makedirs()

        with open(self.__config_file_path, mode="wt", encoding=self.__encoding) as config_file:
            config_file.write(str(data))

        if set_executable:
            self.__config_file_path.add_executable()
        return self.__config_file_path

    def set_with_backup(self, data: typing.Any, set_executable: bool = False, is_rewrite_backup: bool = False) -> Path:
        if self.__config_file_path.exists():
            self.__last_backup_file_path = self.__config_file_path.create_backup(
                backup_file_path=self.__last_backup_file_path if is_rewrite_backup else None)
        self.set(data, set_executable)
        return self.get_last_backup_file_path()

    def get_last_backup_file_path(self) -> Path | None:
        return self.__last_backup_file_path

    def restore_from_backup(self, is_remove_backup: bool = False) -> bool:
        if not self.__last_backup_file_path or not self.__last_backup_file_path.exists():
            return False

        self.__config_file_path.restore_from_backup(self.get_last_backup_file_path(), is_remove_backup=is_remove_backup)

    def __makedirs(self) -> None:
        self.__config_file_path.parent.makedirs()


class JsonConfigWriter:
    def __init__(self, config_file_path: str | os.PathLike[str], encoding: str = "utf-8"):
        self.__text_config_writer = TextConfigWriter(config_file_path=config_file_path, encoding=encoding)

    def set(self, data: JsonType) -> Path:
        return self.__text_config_writer.set(json.dumps(data, sort_keys=True, indent=4))
