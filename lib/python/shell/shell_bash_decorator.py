from lib.python.utils import EscapeLiteral


class ShellBashDecorator:
    __ENCODE_TABLE_FOR_REDUCE_NEW_LINE_ESCAPING = [("\\\r\n", ""), ("\\\n\r", ""), ("\\\n", ""), ("\\\r", "")]

    __ENCODE_TABLE = [("\\", "\\\\"), ("$", "\\$"), ("\"", "\\\"")]

    def __init__(self):
        pass

    def __call__(self, func):
        def __decorator_func(*args, **kwargs):
            cmd_line = func(*args, **kwargs)
            cmd_line = self.full_escape_cmd_line(cmd_line)
            self.__check_cmd_line(cmd_line)
            return f'bash -l -c "{cmd_line}"'

        return __decorator_func

    def full_escape_cmd_line(self, cmd_line: str) -> str:
        return EscapeLiteral(
            encode_table=self.__ENCODE_TABLE_FOR_REDUCE_NEW_LINE_ESCAPING + self.__ENCODE_TABLE).encode(cmd_line)

    def escape_cmd_line_for_win(self, cmd_line: str) -> str:
        return EscapeLiteral(encode_table=[("\\", "\\\\")]).encode(cmd_line)

    def __check_cmd_line(self, cmd_line: str) -> None:
        if "\n" in cmd_line or "\r" in cmd_line:
            raise Exception("[bash] only single string command available")
