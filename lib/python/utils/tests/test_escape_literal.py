import unittest

from ..escape_literal import EscapeLiteral


class UnitTest_EscapeLiteral(unittest.TestCase):

    def self_test(self):
        target_string = "\rhello\\\n\"world!\'\n\r\\hello world"

        escape_literal = EscapeLiteral()
        encoded_string = escape_literal.encode(target_string)
        decoded_string = escape_literal.decode(encoded_string)
        self.assertEqual(target_string, decoded_string)
