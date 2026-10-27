"""Асинхронный запуск команд и скриптов"""

import asyncio
import os
import shlex
import typing

from lib.python.logger.logger import Logger

type RunnableDescriptorType = tuple[str | os.PathLike[str], bool, bool, bool]
type CommandResultType = tuple[int, int | None]
type RunnableResultType = CommandResultType | BaseException


class AsyncRunner:
    """Асинхронный запуск команд и скриптов

    .. note::
       Команды с ``is_background_executing`` запускаются параллельно, остальные — последовательно
    """

    STDOUT_DECODE = "utf-8"
    STDERR_DECODE = STDOUT_DECODE

    def __init__(self) -> None:
        """Инициализировать runner"""
        self.__runnable_descriptor_list_parallel: list[RunnableDescriptorType] = []
        self.__runnable_descriptor_list_sequential: list[RunnableDescriptorType] = []

    def add(self, script_path_or_command: str | os.PathLike[str], is_background_executing: bool = False,
            shell: bool = True, log_stdout: bool = True, log_stderr: bool = True) -> None:
        """Добавить команду в очередь

        :param script_path_or_command: Команда или путь до скрипта
        :param is_background_executing: Запускать в фоне (параллельно)
        :param shell: Запускать через shell
        :param log_stdout: Логировать stdout
        :param log_stderr: Логировать stderr
        """
        if is_background_executing:
            self.__runnable_descriptor_list_parallel.append((script_path_or_command, shell, log_stdout, log_stderr))
        else:
            self.__runnable_descriptor_list_sequential.append((script_path_or_command, shell, log_stdout, log_stderr))

    async def run_all(self) -> list[RunnableResultType]:
        """Запустить все добавленные команды

        :return: Результаты выполнения
        """
        runnable_list = [
            self.__run_sequential(*self.__runnable_descriptor_list_sequential,
                                  handler=lambda x: self.__run(x)),
            self.__run_parallel(*self.__runnable_descriptor_list_parallel,
                                handler=lambda x: self.__run(x))]

        result = await self.__run_parallel(*runnable_list)
        return typing.cast(list[RunnableResultType], result[0] + result[1])

    async def __run(self, runnable_descriptor: RunnableDescriptorType) -> CommandResultType:
        """Запустить одну команду

        :param runnable_descriptor: Описание команды
        :return: PID и код возврата
        """
        script_path_or_command, shell, log_stdout, log_stderr = runnable_descriptor

        Logger.instance().debug(f'[ScriptRun] Start "{script_path_or_command}"')

        if shell:
            process = await asyncio.create_subprocess_shell(str(script_path_or_command),
                                                            stdout=asyncio.subprocess.PIPE,
                                                            stderr=asyncio.subprocess.PIPE)
        else:
            command_with_args = shlex.split(str(script_path_or_command))
            if not command_with_args:
                raise RuntimeError(f'[ScriptRun] Command IS EMPTY: "{script_path_or_command}"')
            command = command_with_args[0]
            args = command_with_args[1:]
            process = await asyncio.create_subprocess_exec(command, *args, stdout=asyncio.subprocess.PIPE,
                                                           stderr=asyncio.subprocess.PIPE)

        stdout = process.stdout
        stderr = process.stderr
        if stdout is None or stderr is None:
            raise RuntimeError(f'[ScriptRun] Process streams NOT AVAILABLE: "{script_path_or_command}"')

        pid = process.pid
        try:
            Logger.instance().debug(f'[ScriptRun] Started [pid={pid}] "{script_path_or_command}"')
            await self.__run_parallel(self.__log_stdout(stdout, is_log=log_stdout),
                                      self.__log_stderr(stderr, is_log=log_stderr))
            return await self.__wait(process, script_path_or_command)
        except asyncio.CancelledError:
            process.kill()
            Logger.instance().debug(f'[ScriptRun] KILL [pid={pid}] "{script_path_or_command}"')
            return await self.__wait(process, script_path_or_command)

    async def __wait(self, process: asyncio.subprocess.Process,
                     script_path_or_command: str | os.PathLike[str]) -> CommandResultType:
        """Дождаться завершения процесса

        :param process: Процесс
        :param script_path_or_command: Команда или путь до скрипта
        :return: PID и код возврата
        """
        await process.wait()
        Logger.instance().debug(
            f'[ScriptRun] End [pid={process.pid}, exit_code={process.returncode}] "{script_path_or_command}"')
        return process.pid, process.returncode

    async def __run_parallel(self, *task_list: typing.Any,
                             handler: typing.Callable[[typing.Any], typing.Any] | None = None) -> list[typing.Any]:
        """Запустить задачи параллельно

        :param task_list: Список задач
        :param handler: Обработчик задачи
        :return: Результаты выполнения
        """
        return await asyncio.gather(*self.__prepare_task_list(*task_list, handler=handler), return_exceptions=True)

    async def __run_sequential(self, *task_list: typing.Any,
                               handler: typing.Callable[[typing.Any], typing.Any] | None = None) -> list[typing.Any]:
        """Запустить задачи последовательно

        :param task_list: Список задач
        :param handler: Обработчик задачи
        :return: Результаты выполнения
        """
        result = []
        for task in self.__prepare_task_list(*task_list, handler=handler):
            try:
                result.append(await task)
            except Exception as ex:
                result.append(ex)
        return result

    def __prepare_task_list(self, *task_list: typing.Any,
                            handler: typing.Callable[[typing.Any], typing.Any] | None = None) -> list[typing.Any]:
        """Подготовить список задач

        :param task_list: Список задач
        :param handler: Обработчик задачи
        :return: Подготовленный список задач
        """
        result = []
        for task in task_list:
            if isinstance(task, list):
                result.extend(self.__prepare_task_list(*task, handler=handler))
                continue

            if handler is not None:
                task = handler(task)
            if task is None or isinstance(task, Exception):
                task = self.__pass_value(task)

            result.append(task)
        return result

    @staticmethod
    async def __pass_value(val: typing.Any) -> typing.Any:
        """Вернуть значение как есть

        :param val: Значение
        :return: Значение
        """
        return val

    async def __log_stdout(self, stdout_stream: asyncio.StreamReader, is_log: bool) -> None:
        """Логировать stdout процесса

        :param stdout_stream: Поток stdout
        :param is_log: Логировать вывод
        """
        while True:
            buffer = await stdout_stream.readline()
            if buffer:
                if is_log:
                    Logger.instance().debug(buffer.decode(self.STDOUT_DECODE))
            else:
                break

    async def __log_stderr(self, stderr_stream: asyncio.StreamReader, is_log: bool) -> None:
        """Логировать stderr процесса

        :param stderr_stream: Поток stderr
        :param is_log: Логировать вывод
        """
        while True:
            buffer = await stderr_stream.readline()
            if buffer:
                if is_log:
                    Logger.instance().error(buffer.decode(self.STDERR_DECODE))
            else:
                break
