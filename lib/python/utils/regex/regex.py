import re


class RegexConstants:
    CAPTURE_ALL = fr"(.*)"
    WHITESPACES = r"\s"
    WHITESPACE_CHARACTER_SET = fr"[{WHITESPACES}]"
    SPACE_SYMBOLS_ZERO_OR_MORE = fr"{WHITESPACE_CHARACTER_SET}*"
    SPACE_SYMBOLS_ONE_OR_MORE = fr"{WHITESPACE_CHARACTER_SET}+"
    NEWLINE_CHARACTER_SET = r"[\n\r]"
    ONE_OR_MORE_NEW_LINES = fr"{NEWLINE_CHARACTER_SET}+"
    ZERO_OR_MORE_NEW_LINES = fr"{NEWLINE_CHARACTER_SET}*"
    ONE_OR_MORE_WHITESPACES = fr"{WHITESPACE_CHARACTER_SET}+"
    ZERO_OR_MORE_WHITESPACES = fr"{WHITESPACE_CHARACTER_SET}*"
    ASCII_LETTER = "a-zA-Z"
    ASCII_LETTER_CHARACTER_SET = f"[{ASCII_LETTER}]"
    ASCII_PRINTABLE = "\\x20-\\x7E"
    ASCII_PRINTABLE_CHARACTER_SET = f"[{ASCII_PRINTABLE}]"

    @staticmethod
    def atomic_group(value):
        return f"(?>{value})"

    @staticmethod
    def to_character_set(character_set, is_remove_duplicate=True):
        result = ""
        if isinstance(character_set, list) or isinstance(character_set, set):
            for item in character_set:
                result += RegexConstants.to_character_set(item)
            result = RegexConstants.to_character_set(result)
        elif isinstance(character_set, str):
            if is_remove_duplicate:
                character_set_as_list = list(set(character_set))
                character_set_as_list.sort()
                result = "".join(character_set_as_list)
            else:
                result = character_set
        return result

    @staticmethod
    def character_set_escape(character_set, is_remove_duplicate=True):
        return re.escape(RegexConstants.to_character_set(character_set, is_remove_duplicate))
