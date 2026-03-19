import datetime
import logging
import logging.handlers
import os
import pathlib
import sys


class Logger:
    """Логгер проекта"""

    class LoggerImpl:
        """Имплементация логгера (singleton)"""

        __LOG_NAME: str = os.environ.get("CONFIG_PROJECT_INSTANCE", "HomeVpn")
        """
        Метка логгера, имя файла лога
        
        .. note::
            Используется имя экземпляра проекта, см. переменную окружения CONFIG_PROJECT_INSTANCE.
            Если переменная окружения не задана используется умолчательное имя "HomeVpn"
        """

        def __init__(self):
            self.__logger = logging.getLogger(self.__LOG_NAME)
            self.__logger.setLevel(logging.DEBUG)
            file_handler = logging.handlers.TimedRotatingFileHandler(self.__get_log_file_path(),
                                                                     when='midnight', encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(
                logging.Formatter(
                    fmt='{asctime} {levelname: <8} {message} [{process}][{thread}] <{funcName}:{lineno}>',
                    style='{'))
            self.__logger.addHandler(file_handler)

            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(logging.Formatter(fmt='{message}', style='{'))
            self.__logger.addHandler(console_handler)

        def get_logger(self) -> logging.Logger:
            """
            Получить логгер

            :return: Логгер
            """
            return self.__logger

        def __get_log_file_path(self) -> pathlib.Path:
            """
            Получить путь до файла лога

            :return: Путь до файла лога
            """
            return self.__get_logging_dir_path() / f"{datetime.datetime.now():%Y-%m-%d}_{self.__LOG_NAME}.log"

        def __get_logging_dir_path(self) -> pathlib.Path:
            """
            Получить путь до директории записи логов

            .. note::
                Если целевой директории не существует, она будет создана

            :return: Путь до директории записи логов
            """
            result = self.__get_project_cwd_path() / "logs"
            result.mkdir(parents=True, exist_ok=True)
            return result

        def __get_project_cwd_path(self) -> pathlib.Path:
            """
            Получить путь до рабочей директории проекта (корень проекта)

            .. note::
                Используется переменная окружения HOME_VPN_PROJECT_ROOT, если задана.
                Если не задана, то используется текущая рабоча директория (PWD)

            :return: Путь до директории записи логов
            """
            return pathlib.Path(os.environ.get("HOME_VPN_PROJECT_ROOT", pathlib.Path.cwd()))

    __instance = LoggerImpl()
    """Единственный (статический) экземпляр логгера (singleton)"""

    @staticmethod
    def instance() -> logging.Logger:
        """
        Получить экземпляр логгера

        :return: Экземпляр логгера
        """
        return Logger.__instance.get_logger()
