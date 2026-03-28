import unittest

from ..bit_utils import BitUtils


class UnitTest_BitUtils(unittest.TestCase):

    def test_is_decimal(self):
        ref_table = {
            "1": [(10, True), (16, False), (2, False), (8, False)],
            "-1": [(10, True), (16, False), (2, False), (8, False)],
            "0": [(10, True), (16, False), (2, False), (8, False)],
            "9999": [(10, True), (16, False), (2, False), (8, False)],
            "-9999": [(10, True), (16, False), (2, False), (8, False)],
            "+9999": [(10, True), (16, False), (2, False), (8, False)],
            "0x0": [(10, False), (16, True), (2, False), (8, False)],
            "0x00": [(10, False), (16, True), (2, False), (8, False)],
            "0x0000": [(10, False), (16, True), (2, False), (8, False)],
            "0x00000000": [(10, False), (16, True), (2, False), (8, False)],
            "0x0000000000000000": [(10, False), (16, True), (2, False), (8, False)],
            "0x00000000000000000000000000000000": [(10, False), (16, True), (2, False), (8, False)],
            "-0xff": [(10, False), (16, True), (2, False), (8, False)],
            "+0xFe": [(10, False), (16, True), (2, False), (8, False)],
            "+0x0000123456789ABCDEF": [(10, False), (16, True), (2, False), (8, False)],
            "-0xFFFFFFFFFFFFFFFF": [(10, False), (16, True), (2, False), (8, False)],
            "+0xFFFFFFFFFFFFFFFF": [(10, False), (16, True), (2, False), (8, False)],
            "0b0": [(10, False), (16, False), (2, True), (8, False)],
            "0b00000000": [(10, False), (16, False), (2, True), (8, False)],
            "-0b010101010101": [(10, False), (16, False), (2, True), (8, False)],
            "+0b010101010101": [(10, False), (16, False), (2, True), (8, False)],
            "01": [(10, False), (16, False), (2, False), (8, True)],
            "-01": [(10, False), (16, False), (2, False), (8, True)],
            "+01": [(10, False), (16, False), (2, False), (8, True)],
            "07": [(10, False), (16, False), (2, False), (8, True)],
            "00": [(10, False), (16, False), (2, False), (8, True)],
            "01234567890ABCDEF": [(10, False), (16, False), (2, False), (8, False)]
        }

        for key, table in ref_table.items():
            for base, result in table:
                if base == 10:
                    self.assertEqual(BitUtils.is_decimal(key), result, f"base={base}, key={key}")
                elif base == 16:
                    self.assertEqual(BitUtils.is_hexadecimal(key), result, f"base={base}, key={key}")
                elif base == 2:
                    self.assertEqual(BitUtils.is_binary(key), result, f"base={base}, key={key}")
                elif base == 8:
                    self.assertEqual(BitUtils.is_octal(key), result, f"base={base}, key={key}")
                else:
                    self.assertTrue(False, f"Unknown base={base}")

    def test_get_digit_count(self):
        ref_table = {
            "9999": (10, 4),
            "10": (10, 2),
            "0xFFFF": (16, 4),
            "0x00FFFF": (16, 4),
            "0xFFFFFFFF": (16, 8),
            "0xFFFFFFFFFFFFFFFF": (16, 16),
            "0b0101": (2, 3),
            "012": (8, 2)
        }

        for key, value in ref_table.items():
            base, result = value
            self.assertEqual(BitUtils.get_digit_count(int(key, base), base), result, f"base={base}, key={key}")
