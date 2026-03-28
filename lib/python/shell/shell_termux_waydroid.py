from lib.python.types import Path

from shell_bash_decorator import ShellBashDecorator

class ShellTermuxWaydroid:
    def __init__(self):
        pass

    def __call__(self, func):
        def __decorator_func(*args, **kwargs) -> str:
            cmd_line = func(*args, **kwargs)
            cmd_line = ShellBashDecorator().full_escape_cmd_line(cmd_line)
            return f'WAYDROID_TRY_RUN_COMMAND_OVER_SSH= "{self.get_waydroid_termux_shell_run_command_script_path()}" "{cmd_line}"'

        return __decorator_func

    def get_waydroid_termux_shell_run_command_script_path(self) -> Path:
        return Path("scripts/waydroid-termux-shell-run-command.sh")
