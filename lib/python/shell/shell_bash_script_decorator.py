from lib.python.utils import apply_decorators

from shell_bash_decorator import ShellBashDecorator


class ShellBashScriptDecorator:
    TEMP_PATH = "TEMP_PATH"

    def __init__(self, call_wrapper_decorator_list, temp_script_file_extension: str = ""):
        self.__call_wrapper_decorator_list = call_wrapper_decorator_list
        self.__temp_script_file_extension = temp_script_file_extension
        self.__script_file_path = f'${self.TEMP_PATH}'

    def __call__(self, func):
        @apply_decorators(self.__call_wrapper_decorator_list)
        def __wrapper():
            return self.__script_file_path

        def __decorator_func(*args, **kwargs):
            cmd_line = func(*args, **kwargs)
            cmd_line = ShellBashDecorator().full_escape_cmd_line(cmd_line)
            call_script_cmd_line = __wrapper()
            # Для wine директория /tmp не годится, т.к. монтируется в wine'е в режиме noexec
            return f'{self.TEMP_PATH}="$(mktemp ~/XXXXXXXXX{self.__temp_script_file_extension})" && trap "rm -f \"{self.__script_file_path}\"" EXIT && echo "{cmd_line}" > "{self.__script_file_path}" && chmod +x "{self.__script_file_path}" && {call_script_cmd_line}'

        return __decorator_func
