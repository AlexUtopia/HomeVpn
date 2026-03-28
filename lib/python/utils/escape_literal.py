

class EscapeLiteral:
    DECODE_TABLE_DEFAULT = [("\\\\", "\\"), ("\\\"", "\""), ("\\\'", "'"), ("\\n", "\n"),
                            ("\\r", "\r")]

    ENCODE_TABLE_DEFAULT = [("\\", "\\\\"), ("\"", "\\\""), ("'", "\\\'"), ("\n", "\\n"),
                            ("\r", "\\r")]

    def __init__(self, decode_table: list[tuple[str, str]] = DECODE_TABLE_DEFAULT,
                 encode_table: list[tuple[str, str]] = ENCODE_TABLE_DEFAULT):
        self.__decode_table = decode_table
        self.__encode_table = encode_table

    def decode(self, target_string: str) -> str:
        result = target_string
        for escape_literal, replace_literal in self.__decode_table:
            result = result.replace(escape_literal, replace_literal)
        return result

    def encode(self, target_string: str) -> str:
        result = target_string
        for replace_literal, escape_literal in self.__encode_table:
            result = result.replace(replace_literal, escape_literal)
        return result
