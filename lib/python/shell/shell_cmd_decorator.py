import os
import pathlib

from lib.python.utils import EscapeLiteral


# fixme utopia Экранировать
#  https://ss64.com/nt/syntax-esc.html
#  https://stackoverflow.com/questions/10296162/escaping-special-characters-in-cmd
#  https://www.google.com/search?q=windows+cmd+escape+literal&newwindow=1&sca_esv=e4930b54a8b6c4ed&sxsrf=ANbL-n5t3-PS6ZgaPr3o5FZu5HpW1USBkg%3A1768600370106&ei=MrNqaeqWBo-D1fIP4NeAwQU&ved=0ahUKEwjq97zmhZGSAxWPQVUIHeArIFgQ4dUDCBE&uact=5&oq=windows+cmd+escape+literal&gs_lp=Egxnd3Mtd2l6LXNlcnAiGndpbmRvd3MgY21kIGVzY2FwZSBsaXRlcmFsMgUQIRigATIFECEYoAEyBRAhGJ8FSO3NA1AAWJbMA3ABeAGQAQCYAWWgAeQQqgEEMjYuMbgBA8gBAPgBAZgCG6ACnRPCAgoQIxiABBgnGIoFwgIEECMYJ8ICDRAAGIAEGLEDGEMYigXCAhEQLhiABBixAxjRAxiDARjHAcICCxAAGIAEGLEDGIMBwgIFEAAYgATCAggQABiABBixA8ICERAAGIAEGLEDGIMBGIoFGI0GwgIQEAAYgAQYsQMYQxiDARiKBcICChAAGIAEGEMYigXCAgoQABiABBgUGIcCwgIHEAAYgAQYCsICCBAAGIAEGMsBwgIGEAAYBxgewgIIEAAYExgHGB7CAgQQABgewgIHECEYoAEYCsICBBAhGBWYAwCSBwUxNy4xMKAH86IBsgcFMTYuMTC4B5ATwgcKMC4xLjEyLjkuNcgHpgKACAA&sclient=gws-wiz-serp
#  %COMSPEC%
class ShellCmdDecorator:
    __ENCODE_TABLE_FOR_REDUCE_NEW_LINE_ESCAPING = [("^\r\n", ""), ("^\n\r", ""), ("^\n", ""), ("^\r", "")]

    __ENCODE_TABLE = [("^", "^^"), ("&", "^&"), ("%", "%%"), ("|", "^|"), ("\"", "\"\"")]

    def __init__(self, cmd_path: str | os.PathLike[str] = r'cmd.exe', is_force_call_cmd: bool = True):
        self.__cmd_path = pathlib.Path(os.path.expandvars(cmd_path))
        self.__is_force_call_cmd = is_force_call_cmd

    def __call__(self, func):
        def __decorator_func(*args, **kwargs):
            cmd_line = func(*args, **kwargs)
            cmd_line = self.full_escape_cmd_line(cmd_line)
            self.__check_cmd_line(cmd_line)
            return f'"{self.__cmd_path}" /q /c "{cmd_line}"'

        return __decorator_func

    def full_escape_cmd_line(self, cmd_line: str) -> str:
        return EscapeLiteral(
            encode_table=self.__ENCODE_TABLE_FOR_REDUCE_NEW_LINE_ESCAPING + self.__ENCODE_TABLE).encode(cmd_line)

    def __check_cmd_line(self, cmd_line: str) -> None:
        if "\n" in cmd_line or "\r" in cmd_line:
            raise Exception("[cmd] only single string command available")
