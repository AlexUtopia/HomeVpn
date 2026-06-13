from lib.python.utils import EscapeLiteral, ShellSerializer


class QemuSerializer(ShellSerializer):
    class QemuEscapeLiteral(EscapeLiteral):
        def __init__(self):
            super().__init__(encode_table=[(",", ",,")])

    def __init__(self):
        super().__init__(nested_serializer=ShellSerializer(quotes_for_string_value="",
                                                           key_value_separator_table=[
                                                               {"prefix": "", "separator": "="}],
                                                           pair_separator=",",
                                                           escape_literal=QemuSerializer.QemuEscapeLiteral(),
                                                           nested_serializer=ShellSerializer(quotes_for_string_value="",
                                                                                             key_value_separator_table=[
                                                                                                 {"prefix": "",
                                                                                                  "separator": "="}],
                                                                                             pair_separator=",",
                                                                                             escape_literal=QemuSerializer.QemuEscapeLiteral()),
                                                           nested_key_value_separator=","
                                                           ))
