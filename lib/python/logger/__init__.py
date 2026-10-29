"""Логгер проекта

.. note::
   Логгер пишет одновременно в файл ``logs/<дата>_<имя_экземпляра>.log`` и в stdout
"""

from .logger import Logger

__all__ = ["Logger"]
