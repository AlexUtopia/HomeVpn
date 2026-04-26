from lib.python.utils.regex import RegexConstants


class String(str):

    @staticmethod
    def get_regex() -> str:
        return f".+"


class StringAsciiLetter(str):

    @staticmethod
    def get_regex() -> str:
        return f"{RegexConstants.ASCII_LETTER_CHARACTER_SET}+"


class StringAsciiPrintable(str):

    @staticmethod
    def get_regex() -> str:
        return f"{RegexConstants.ASCII_PRINTABLE_CHARACTER_SET}+"


class StringAsciiWords(str):

    @staticmethod
    def get_regex() -> str:
        return fr"[\w \-,.]+"
