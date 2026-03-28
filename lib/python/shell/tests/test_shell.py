import getpass
import platform
import subprocess
import unittest

from lib.python.system import CurrentOs
from lib.python.utils import apply_decorators

from ..run_in_bash_shell_decorator import RunInBashShellDecorator
from ..run_in_cmd_shell_decorator import RunInCmdShellDecorator
from ..shell_docker_decorator import ShellDockerDecorator
from ..shell_msys2_decorator import ShellMsys2Decorator
from ..shell_termux_waydroid import ShellTermuxWaydroid
from ..shell_wine_decorator import ShellWineDecorator


class UnitTest_RunInShell(unittest.TestCase):
    ENCODING = "utf-8"
    SSH_CLIENT_CONNECTION_ERROR_CODE = 255

    TEST_DATA_LIST = [
        {
            "description": "Запуск msys2 bash через wine (с использованием docker, только linux:x86_64)",
            "decorator_list": [ShellDockerDecorator(),
                               RunInCmdShellDecorator(shell_wine_decorator=ShellWineDecorator(wine_path="wine",
                                                                                              is_crutch_for_msys2_over_wine=True)),
                               ShellMsys2Decorator()],
            "test_case_list":
                [
                    {
                        "cmd": r'echo "\"TEST message $SYSTEMDRIVE $WINEHOMEDIR $MSYSTEM_PREFIX\""',
                        "cmd_for_executing": {
                            "linux:x86_64": r'''docker run -it "ghcr.io/msys2/msys2-docker-experimental" bash -l -c "TEMP_PATH=\"\$(mktemp ~/XXXXXXXXX.cmd)\" && trap \"rm -f \"\$TEMP_PATH\"\" EXIT && echo \"\\\"%SYSTEMDRIVE%\\\\msys64\\\\msys2_shell.cmd\\\" -no-start -clang64 -defterm -c \\\"echo \\\"\\\"\\\\\\\\\\\"\\\"TEST message \\\$SYSTEMDRIVE \\\$WINEHOMEDIR \\\$MSYSTEM_PREFIX\\\\\\\\\\\"\\\"\\\"\\\"\\\"\" > \"\$TEMP_PATH\" && chmod +x \"\$TEMP_PATH\" && sed -i 's/delims=,;=	 \"/delims=,;= \"/g' ~/.wine/drive_c/msys64/msys2_shell.cmd && WINEDEBUG=-all && wine \"cmd.exe\" /q /c \"\$TEMP_PATH\""'''
                        },
                        "stdout": r'''"TEST message C: \??\Z:\root /clang64"'''
                    },
                    {
                        "cmd": r'exit 17',
                        "cmd_for_executing": {
                            "linux:x86_64": r'''docker run -it "ghcr.io/msys2/msys2-docker-experimental" bash -l -c "TEMP_PATH=\"\$(mktemp ~/XXXXXXXXX.cmd)\" && trap \"rm -f \"\$TEMP_PATH\"\" EXIT && echo \"\\\"%SYSTEMDRIVE%\\\\msys64\\\\msys2_shell.cmd\\\" -no-start -clang64 -defterm -c \\\"exit 17\\\"\" > \"\$TEMP_PATH\" && chmod +x \"\$TEMP_PATH\" && sed -i 's/delims=,;=	 \"/delims=,;= \"/g' ~/.wine/drive_c/msys64/msys2_shell.cmd && WINEDEBUG=-all && wine \"cmd.exe\" /q /c \"\$TEMP_PATH\""'''
                        },
                        "exit_code": 17
                    },
                    {
                        "cmd": r'whoami',
                        "cmd_for_executing": {
                            "linux:x86_64": r'''docker run -it "ghcr.io/msys2/msys2-docker-experimental" bash -l -c "TEMP_PATH=\"\$(mktemp ~/XXXXXXXXX.cmd)\" && trap \"rm -f \"\$TEMP_PATH\"\" EXIT && echo \"\\\"%SYSTEMDRIVE%\\\\msys64\\\\msys2_shell.cmd\\\" -no-start -clang64 -defterm -c \\\"whoami\\\"\" > \"\$TEMP_PATH\" && chmod +x \"\$TEMP_PATH\" && sed -i 's/delims=,;=	 \"/delims=,;= \"/g' ~/.wine/drive_c/msys64/msys2_shell.cmd && WINEDEBUG=-all && wine \"cmd.exe\" /q /c \"\$TEMP_PATH\""'''
                        },
                        "stdout": getpass.getuser()
                    },
                    {
                        "cmd": r'uname -o',
                        "cmd_for_executing": {
                            "linux:x86_64": r'''docker run -it "ghcr.io/msys2/msys2-docker-experimental" bash -l -c "TEMP_PATH=\"\$(mktemp ~/XXXXXXXXX.cmd)\" && trap \"rm -f \"\$TEMP_PATH\"\" EXIT && echo \"\\\"%SYSTEMDRIVE%\\\\msys64\\\\msys2_shell.cmd\\\" -no-start -clang64 -defterm -c \\\"uname -o\\\"\" > \"\$TEMP_PATH\" && chmod +x \"\$TEMP_PATH\" && sed -i 's/delims=,;=	 \"/delims=,;= \"/g' ~/.wine/drive_c/msys64/msys2_shell.cmd && WINEDEBUG=-all && wine \"cmd.exe\" /q /c \"\$TEMP_PATH\""'''
                        },
                        "stdout": "Msys"
                    }
                    # fixme utopia Можно отладить/протестировать setup-packges.sh для msys2
                ]
        },
        {
            "description": "Запуск cmd.exe (кроссплатформенно)",
            "decorator_list": [RunInCmdShellDecorator()],
            "test_case_list":
                [
                    {
                        "cmd": r'echo "TEST message %SYSTEMDRIVE% %COMSPEC%"',
                        "cmd_for_executing": {
                            "linux": r'''bash -l -c "TEMP_PATH=\"\$(mktemp ~/XXXXXXXXX.cmd)\" && trap \"rm -f \"\$TEMP_PATH\"\" EXIT && echo \"echo \\\"TEST message %SYSTEMDRIVE% %COMSPEC%\\\"\" > \"\$TEMP_PATH\" && chmod +x \"\$TEMP_PATH\" && WINEDEBUG=-all && /opt/wine-stable/bin/wine \"cmd.exe\" /q /c \"\$TEMP_PATH\""''',
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
                            "linux": r'''bash -l -c "TEMP_PATH=\"\$(mktemp ~/XXXXXXXXX.cmd)\" && trap \"rm -f \"\$TEMP_PATH\"\" EXIT && echo \"exit 17\" > \"\$TEMP_PATH\" && chmod +x \"\$TEMP_PATH\" && WINEDEBUG=-all && /opt/wine-stable/bin/wine \"cmd.exe\" /q /c \"\$TEMP_PATH\""''',
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
                            "linux": r'''bash -l -c "TEMP_PATH=\"\$(mktemp ~/XXXXXXXXX.cmd)\" && trap \"rm -f \"\$TEMP_PATH\"\" EXIT && echo \"whoami\" > \"\$TEMP_PATH\" && chmod +x \"\$TEMP_PATH\" && WINEDEBUG=-all && /opt/wine-stable/bin/wine \"cmd.exe\" /q /c \"\$TEMP_PATH\""''',
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

    def test(self):
        for test_data in self.TEST_DATA_LIST:
            for test_case in test_data["test_case_list"]:
                for os_and_arch, expected_cmd_for_executing in test_case["cmd_for_executing"].items():
                    if CurrentOs.check_os_and_arch(os_and_arch):
                        test_description = f'[{os_and_arch}] Test "{test_data["description"]}" | {test_case["cmd"]}'

                        expected_stdout = None
                        if isinstance(expected_cmd_for_executing, tuple):
                            expected_stdout = expected_cmd_for_executing[1]
                            expected_cmd_for_executing = expected_cmd_for_executing[0]

                        cmd_for_executing = apply_decorators(test_data["decorator_list"])(lambda: test_case["cmd"])()
                        self.assertEqual(expected_cmd_for_executing, cmd_for_executing,
                                         msg=f'{test_description}\n{cmd_for_executing}')

                        cmd_result = subprocess.run(cmd_for_executing, shell=True, capture_output=True, text=True)
                        if cmd_result.returncode == test_case.get("ignore_exit_code"):
                            continue

                        expected_exit_code = test_case.get("exit_code", 0)
                        self.assertEqual(expected_exit_code, cmd_result.returncode, msg=test_description)

                        if not expected_stdout:
                            expected_stdout = test_case.get("stdout")
                        if expected_stdout:
                            self.assertTrue(expected_stdout in cmd_result.stdout,
                                            msg=f'{test_description}\n{str(cmd_result.stdout)}')
