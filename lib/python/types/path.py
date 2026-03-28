from __future__ import annotations

import datetime
import getpass
import os
import pathlib
import shutil
import stat
import typing

from lib.python.system import CurrentOs


class Path(pathlib.Path):
    def __init__(self, *args):
        path = pathlib.Path(*args)
        if not self.is_absolute():
            path = pathlib.Path(os.environ.get("HOME_VPN_PROJECT_ROOT", pathlib.Path.cwd())) / path
        super().__init__(path)

    def with_segments(self, *pathsegments):
        return type(self)(*pathsegments)

    @staticmethod
    def get_home_dir_path(user: str = getpass.getuser()) -> Path | None:
        if CurrentOs.is_termux():
            user = ""

        result = Path(f"~{user}").expanduser()
        if result.exists():
            return result
        return None

    def file_exists(self) -> bool:
        return self.exists() and self.is_file()

    def makedirs(self) -> None:
        self.mkdir(parents=True, exist_ok=True)

    def exists_by_wildcard(self, wildcard: str):
        return next(self.glob(wildcard), None) is None

    def copy_from(self, path: str | os.PathLike[str]) -> None:
        shutil.copy2(Path(path), self)

    # fixme utopia backup для файла и для директории
    def create_backup(self, backup_file_path: str | os.PathLike[str] | None = None,
                      backup_prefix: str = f"unused_since_{datetime.datetime.now():%Y-%m-%dT%H_%M_%S_%f%z}_") -> typing.Self | None:
        if not self.file_exists():
            return None

        if not backup_file_path:
            backup_file_path = Path(self.parent / f"{backup_prefix}{self.name}")
        else:
            backup_file_path = Path(backup_file_path)
        backup_file_path.copy_from(self)
        return backup_file_path

    # fixme utopia backup для файла и для директории
    def restore_from_backup(self, backup_file_path: str | os.PathLike[str], is_remove_backup: bool = False) -> bool:
        backup_file_path_as_path = Path(backup_file_path)
        if not backup_file_path_as_path.exists():
            return False

        self.copy_from(backup_file_path_as_path)
        if is_remove_backup:
            backup_file_path_as_path.unlink()
        return True

    def add_executable(self) -> None:
        mode = self.stat().st_mode
        mode |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        self.chmod(mode)
