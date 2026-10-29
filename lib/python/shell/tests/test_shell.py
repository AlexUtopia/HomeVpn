"""Тесты запуска команд в командных оболочках"""

import getpass
import platform
import shutil
import subprocess
import typing
import unittest

from lib.python.system.current_os import CurrentOs
from lib.python.utils.decorator import apply_decorators

from ..run_in_bash_shell_decorator import RunInBashShellDecorator
from ..run_in_cmd_shell_decorator import RunInCmdShellDecorator
from ..shell_docker_decorator import ShellDockerDecorator
from ..shell_msys2_decorator import ShellMsys2Decorator
from ..shell_termux_waydroid import ShellTermuxWaydroid
from ..shell_wine_decorator import ShellWineDecorator


CmdForExecuting = dict[str, str | tuple[str, str]]


class TestCase(typing.TypedDict, total=False):
    """Тестовый случай запуска команды"""

    cmd: str
    cmd_for_executing: CmdForExecuting
    stdout: str
    exit_code: int
    ignore_exit_code: int


class TestData(typing.TypedDict):
    """Набор тестовых случаев для одного декоратора"""

    description: str
    requires: list[str]
    decorator_list: list[typing.Callable[..., typing.Any]]
    test_case_list: list[TestCase]


class UnitTest_RunInShell(unittest.TestCase):
    """Тесты запуска команд в командных оболочках"""

    ENCODING = "utf-8"
    SSH_CLIENT_CONNECTION_ERROR_CODE = 255

    TEST_DATA_LIST: list[TestData] = [
        {
            "description": "Запуск msys2 bash через wine (с использованием docker, только linux:x86_64)",
            "requires": ["docker"],
            "decorator_list": [ShellDockerDecorator(),
                               RunInCmdShellDecorator(shell_wine_decorator=ShellWineDecorator(wine_path="wine",
                                                                                              is_crutch_for_msys2_over_wine=True)),
                               ShellMsys2Decorator()],
            "test_case_list":
                [
                    {
                        "cmd": r'echo "\"TEST message $SYSTEMDRIVE $WINEHOMEDIR $MSYSTEM_PREFIX\""',
                        "cmd_for_executing": {
                            "linux:x86_64": r'''docker run "ghcr.io/msys2/msys2-docker-experimental" bash -l -c "TEMP_PATH=\"\$(mktemp ~/XXXXXXXXX.cmd)\" && trap \"rm -f \"\$TEMP_PATH\"\" EXIT && echo \"\\\"%SYSTEMDRIVE%\\\\msys64\\\\msys2_shell.cmd\\\" -no-start -clang64 -defterm -c \\\"echo \\\"\\\"\\\\\\\\\\\"\\\"TEST message \\\$SYSTEMDRIVE \\\$WINEHOMEDIR \\\$MSYSTEM_PREFIX\\\\\\\\\\\"\\\"\\\"\\\"\\\"\" > \"\$TEMP_PATH\" && chmod +x \"\$TEMP_PATH\" && sed -i 's/delims=,;=	 \"/delims=,;= \"/g' ~/.wine/drive_c/msys64/msys2_shell.cmd && WINEDEBUG=-all && \"wine\" \"%COMSPEC%\" /q /c \"\$TEMP_PATH\""'''
                        },
                        "stdout": r'''"TEST message C: \??\Z:\root /clang64"'''
                    },
                    {
                        "cmd": r'exit 17',
                        "cmd_for_executing": {
                            "linux:x86_64": r'''docker run "ghcr.io/msys2/msys2-docker-experimental" bash -l -c "TEMP_PATH=\"\$(mktemp ~/XXXXXXXXX.cmd)\" && trap \"rm -f \"\$TEMP_PATH\"\" EXIT && echo \"\\\"%SYSTEMDRIVE%\\\\msys64\\\\msys2_shell.cmd\\\" -no-start -clang64 -defterm -c \\\"exit 17\\\"\" > \"\$TEMP_PATH\" && chmod +x \"\$TEMP_PATH\" && sed -i 's/delims=,;=	 \"/delims=,;= \"/g' ~/.wine/drive_c/msys64/msys2_shell.cmd && WINEDEBUG=-all && \"wine\" \"%COMSPEC%\" /q /c \"\$TEMP_PATH\""'''
                        },
                        "exit_code": 17
                    },
                    {
                        "cmd": r'whoami',
                        "cmd_for_executing": {
                            "linux:x86_64": r'''docker run "ghcr.io/msys2/msys2-docker-experimental" bash -l -c "TEMP_PATH=\"\$(mktemp ~/XXXXXXXXX.cmd)\" && trap \"rm -f \"\$TEMP_PATH\"\" EXIT && echo \"\\\"%SYSTEMDRIVE%\\\\msys64\\\\msys2_shell.cmd\\\" -no-start -clang64 -defterm -c \\\"whoami\\\"\" > \"\$TEMP_PATH\" && chmod +x \"\$TEMP_PATH\" && sed -i 's/delims=,;=	 \"/delims=,;= \"/g' ~/.wine/drive_c/msys64/msys2_shell.cmd && WINEDEBUG=-all && \"wine\" \"%COMSPEC%\" /q /c \"\$TEMP_PATH\""'''
                        },
                        "stdout": "root"
                    },
                    {
                        "cmd": r'uname -o',
                        "cmd_for_executing": {
                            "linux:x86_64": r'''docker run "ghcr.io/msys2/msys2-docker-experimental" bash -l -c "TEMP_PATH=\"\$(mktemp ~/XXXXXXXXX.cmd)\" && trap \"rm -f \"\$TEMP_PATH\"\" EXIT && echo \"\\\"%SYSTEMDRIVE%\\\\msys64\\\\msys2_shell.cmd\\\" -no-start -clang64 -defterm -c \\\"uname -o\\\"\" > \"\$TEMP_PATH\" && chmod +x \"\$TEMP_PATH\" && sed -i 's/delims=,;=	 \"/delims=,;= \"/g' ~/.wine/drive_c/msys64/msys2_shell.cmd && WINEDEBUG=-all && \"wine\" \"%COMSPEC%\" /q /c \"\$TEMP_PATH\""'''
                        },
                        "stdout": "Msys"
                    }
                    # fixme utopia Можно отладить/протестировать setup-packges.sh для msys2
                ]
        },
        {
            "description": "Запуск cmd.exe (кроссплатформенно)",
            "requires": ["wine"],
            "decorator_list": [RunInCmdShellDecorator()],
            "test_case_list":
                [
                    {
                        "cmd": r'echo "TEST message %SYSTEMDRIVE% %COMSPEC%"',
                        "cmd_for_executing": {
                            "linux": r'''bash -l -c "TEMP_PATH=\"\$(mktemp ~/XXXXXXXXX.cmd)\" && trap \"rm -f \"\$TEMP_PATH\"\" EXIT && echo \"echo \\\"TEST message %SYSTEMDRIVE% %COMSPEC%\\\"\" > \"\$TEMP_PATH\" && chmod +x \"\$TEMP_PATH\" && WINEDEBUG=-all && \"/opt/wine-stable/bin/wine\" \"%COMSPEC%\" /q /c \"\$TEMP_PATH\""''',
                            "Android/termux": "",
                            "windows": "",
                            "msys": "",
                            "cygwin": ""
                        },
                        "stdout": r'''"TEST message C: C:\windows\system32\cmd.exe"'''
                    },
                    {
                        "cmd": r'exit 17',
                        "cmd_for_executing": {
                            "linux": r'''bash -l -c "TEMP_PATH=\"\$(mktemp ~/XXXXXXXXX.cmd)\" && trap \"rm -f \"\$TEMP_PATH\"\" EXIT && echo \"exit 17\" > \"\$TEMP_PATH\" && chmod +x \"\$TEMP_PATH\" && WINEDEBUG=-all && \"/opt/wine-stable/bin/wine\" \"%COMSPEC%\" /q /c \"\$TEMP_PATH\""''',
                            "Android/termux": "",
                            "windows": "",
                            "msys": "",
                            "cygwin": ""
                        },
                        "exit_code": 17
                    },
                    {
                        "cmd": r'whoami',
                        "cmd_for_executing": {
                            "linux": r'''bash -l -c "TEMP_PATH=\"\$(mktemp ~/XXXXXXXXX.cmd)\" && trap \"rm -f \"\$TEMP_PATH\"\" EXIT && echo \"whoami\" > \"\$TEMP_PATH\" && chmod +x \"\$TEMP_PATH\" && WINEDEBUG=-all && \"/opt/wine-stable/bin/wine\" \"%COMSPEC%\" /q /c \"\$TEMP_PATH\""''',
                            "Android/termux": "",
                            "windows": "",
                            "msys": "",
                            "cygwin": ""
                        },
                        "stdout": fr'{platform.node().upper():.15}\{getpass.getuser()}'
                    }
                ]
        },
        {
            "description": "Запуск bash (кроссплатформенно)",
            "requires": [],
            "decorator_list": [RunInBashShellDecorator()],
            "test_case_list":
                [
                    {
                        "cmd": r'echo "\"TEST message\""',
                        "cmd_for_executing": {
                            "linux": r'''bash -l -c "echo \"\\\"TEST message\\\"\""''',
                            "Android/termux": "",
                            "msys": "",
                            "cygwin": ""
                        },
                        "stdout": f'"TEST message"'
                    },
                    {
                        "cmd": r'exit 17',
                        "cmd_for_executing": {
                            "linux": r'''bash -l -c "exit 17"''',
                            "Android/termux": "",
                            "msys": "",
                            "cygwin": ""
                        },
                        "exit_code": 17
                    },
                    {
                        "cmd": "whoami",
                        "cmd_for_executing": {
                            "linux": r'''bash -l -c "whoami"''',
                            "Android/termux": "",
                            "msys": "",
                            "cygwin": ""
                        },
                        "stdout": getpass.getuser()
                    },
                    {
                        "cmd": r'uname -o',
                        "cmd_for_executing": {
                            "linux": (r'''bash -l -c "uname -o"''', "GNU/Linux"),
                            "Android/termux": r'''fixme utopia''',
                            "msys": r'''fixme utopia''',
                            "cygwin": r'''fixme utopia'''
                        }
                    }
                ]
        },
        {
            "description": "Запуск bash в Android/termux (waydroid + termux + ssh сервер)",
            "requires": ["waydroid"],
            "decorator_list": [ShellTermuxWaydroid()],
            "test_case_list":
                [
                    {
                        "cmd": r'echo "\"TEST message $PREFIX\""',
                        "cmd_for_executing": {
                            "linux": fr'''WAYDROID_TRY_RUN_COMMAND_OVER_SSH= "{ShellTermuxWaydroid().get_waydroid_termux_shell_run_command_script_path()}" "echo \"\\\"TEST message \$PREFIX\\\"\""'''
                        },
                        "stdout": f'"TEST message /data/data/com.termux/files/usr"',
                        "ignore_exit_code": SSH_CLIENT_CONNECTION_ERROR_CODE
                    },
                    {
                        "cmd": r'exit 17',
                        "cmd_for_executing": {
                            "linux": fr'''WAYDROID_TRY_RUN_COMMAND_OVER_SSH= "{ShellTermuxWaydroid().get_waydroid_termux_shell_run_command_script_path()}" "exit 17"'''
                        },
                        "exit_code": 17,
                        "ignore_exit_code": SSH_CLIENT_CONNECTION_ERROR_CODE
                    },
                    {
                        "cmd": r'uname -o',
                        "cmd_for_executing": {
                            "linux": fr'''WAYDROID_TRY_RUN_COMMAND_OVER_SSH= "{ShellTermuxWaydroid().get_waydroid_termux_shell_run_command_script_path()}" "uname -o"'''
                        },
                        "stdout": "Android",
                        "ignore_exit_code": SSH_CLIENT_CONNECTION_ERROR_CODE
                    }
                ]
        }
    ]

    @staticmethod
    def _is_requirement_satisfied(requirement: str) -> bool:
        """Проверить доступность внешней зависимости

        :param requirement: Имя зависимости (docker, wine, waydroid)
        :return: ``True``, если зависимость доступна
        """
        if requirement == "docker":
            return shutil.which("docker") is not None
        if requirement == "wine":
            wine_path = ShellWineDecorator.get_wine_executable_path()
            return wine_path.exists() or shutil.which(str(wine_path)) is not None
        if requirement == "waydroid":
            return shutil.which("waydroid") is not None and shutil.which("adb") is not None
        return False

    def _iter_applicable_cases(self) -> typing.Iterator[tuple[TestData, TestCase, str, str, str | None]]:
        """Перебрать тестовые случаи, применимые к текущей ОС и архитектуре

        :return: Итератор кортежей (набор, случай, ОС/архитектура, ожидаемая команда, ожидаемый stdout)
        """
        for test_data in self.TEST_DATA_LIST:
            for test_case in test_data["test_case_list"]:
                for os_and_arch, expected in test_case["cmd_for_executing"].items():
                    if not CurrentOs.check_os_and_arch(os_and_arch):
                        continue

                    if isinstance(expected, tuple):
                        expected_cmd = expected[0]
                        expected_stdout = expected[1]
                    else:
                        expected_cmd = expected
                        expected_stdout = None

                    yield test_data, test_case, os_and_arch, expected_cmd, expected_stdout

    @staticmethod
    def _get_test_description(test_data: TestData, test_case: TestCase, os_and_arch: str) -> str:
        """Сформировать описание тестового случая

        :param test_data: Набор тестовых случаев
        :param test_case: Тестовый случай
        :param os_and_arch: ОС и архитектура
        :return: Описание тестового случая
        """
        return f'[{os_and_arch}] Test "{test_data["description"]}" | {test_case["cmd"]}'

    def test_command_generation(self) -> None:
        """Проверить формирование командной строки для текущей платформы"""
        for test_data, test_case, os_and_arch, expected_cmd, _ in self._iter_applicable_cases():
            with self.subTest(os_and_arch=os_and_arch, cmd=test_case["cmd"]):
                test_description = self._get_test_description(test_data, test_case, os_and_arch)
                actual_cmd = apply_decorators(test_data["decorator_list"])(lambda: test_case["cmd"])()
                self.assertEqual(expected_cmd, actual_cmd, msg=f"{test_description}\n{actual_cmd}")

    def test_execution(self) -> None:
        """Выполнить команды для текущей платформы и проверить результат

        .. note::
           Случаи, для которых недоступны внешние зависимости, пропускаются
        """
        for test_data, test_case, os_and_arch, expected_cmd, expected_stdout in self._iter_applicable_cases():
            with self.subTest(os_and_arch=os_and_arch, cmd=test_case["cmd"]):
                test_description = self._get_test_description(test_data, test_case, os_and_arch)
                missing_requirements = [requirement for requirement in test_data["requires"]
                                        if not self._is_requirement_satisfied(requirement)]
                if missing_requirements:
                    self.skipTest(f"Недоступны зависимости: {', '.join(missing_requirements)}")

                actual_cmd = apply_decorators(test_data["decorator_list"])(lambda: test_case["cmd"])()
                self.assertEqual(expected_cmd, actual_cmd, msg=f"{test_description}\n{actual_cmd}")

                cmd_result = subprocess.run(actual_cmd, shell=True, capture_output=True, text=True)
                if cmd_result.returncode == test_case.get("ignore_exit_code"):
                    continue

                expected_exit_code = test_case.get("exit_code", 0)
                self.assertEqual(expected_exit_code, cmd_result.returncode, msg=test_description)

                if not expected_stdout:
                    expected_stdout = test_case.get("stdout")
                if expected_stdout:
                    self.assertTrue(expected_stdout in cmd_result.stdout,
                                    msg=f'{test_description}\n{str(cmd_result.stdout)}')
