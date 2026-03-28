import asyncio
import shlex

from lib.python.logger import Logger


class AsyncRunner:
    STDOUT_DECODE = "utf-8"
    STDERR_DECODE = STDOUT_DECODE

    def __init__(self):
        self.__runnable_descriptor_list_parallel = []
        self.__runnable_descriptor_list_sequential = []

    def add(self, script_path_or_command, is_background_executing=False, shell=True, log_stdout=True,
            log_stderr=True):
        if bool(is_background_executing):
            self.__runnable_descriptor_list_parallel.append((script_path_or_command, shell, log_stdout, log_stderr))
        else:
            self.__runnable_descriptor_list_sequential.append((script_path_or_command, shell, log_stdout, log_stderr))

    async def run_all(self):
        runnable_list = [
            self.__run_sequential(*self.__runnable_descriptor_list_sequential,
                                  handler=lambda x: self.__run(x)),
            self.__run_parallel(*self.__runnable_descriptor_list_parallel,
                                handler=lambda x: self.__run(x))]

        result = await self.__run_parallel(*runnable_list)
        return result[0] + result[1]

    async def __run(self, runnable_descriptor):
        script_path_or_command, shell, log_stdout, log_stderr = runnable_descriptor

        Logger.instance().debug(f'[ScriptRun] Start "{script_path_or_command}"')

        if shell:
            process = await asyncio.create_subprocess_shell(str(script_path_or_command), stdout=asyncio.subprocess.PIPE,
                                                            stderr=asyncio.subprocess.PIPE)
        else:
            command_with_args = shlex.split(str(script_path_or_command))
            if not command_with_args:
                raise Exception(f'[ScriptRun] Command IS EMPTY: "{script_path_or_command}"')
            command = command_with_args[0]
            args = command_with_args[1:]
            process = await asyncio.create_subprocess_exec(command, *args, stdout=asyncio.subprocess.PIPE,
                                                           stderr=asyncio.subprocess.PIPE)
        pid = process.pid
        try:
            Logger.instance().debug(f'[ScriptRun] Started [pid={pid}] "{script_path_or_command}"')
            await self.__run_parallel(self.__log_stdout(process.stdout, is_log=log_stdout),
                                      self.__log_stderr(process.stderr, is_log=log_stderr))
            return await self.__wait(process, script_path_or_command)
        except asyncio.CancelledError:
            process.kill()
            Logger.instance().debug(f'[ScriptRun] KILL [pid={pid}] "{script_path_or_command}"')
            return await self.__wait(process, script_path_or_command)

    async def __wait(self, process, script_path_or_command):
        await process.wait()
        Logger.instance().debug(
            f'[ScriptRun] End [pid={process.pid}, exit_code={process.returncode}] "{script_path_or_command}"')
        return process.pid, process.returncode

    async def __run_parallel(self, *task_list, handler=None):
        return await asyncio.gather(*self.__prepare_task_list(*task_list, handler=handler), return_exceptions=True)

    async def __run_sequential(self, *task_list, handler=None):
        result = []
        for task in self.__prepare_task_list(*task_list, handler=handler):
            try:
                result.append(await task)
            except Exception as ex:
                result.append(ex)
        return result

    def __prepare_task_list(self, *task_list, handler=None):
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

    async def __pass_value(self, val):
        return val

    async def __log_stdout(self, stdout_stream, is_log):
        while True:
            buffer = await stdout_stream.readline()
            if buffer:
                if bool(is_log):
                    Logger.instance().debug(buffer.decode(self.STDOUT_DECODE))
            else:
                break

    async def __log_stderr(self, stderr_stream, is_log):
        while True:
            buffer = await stderr_stream.readline()
            if buffer:
                if bool(is_log):
                    Logger.instance().error(buffer.decode(self.STDERR_DECODE))
            else:
                break
