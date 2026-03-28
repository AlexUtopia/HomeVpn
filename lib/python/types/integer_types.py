from lib.python.utils.binary import BitUtils


class UInt8Hex(int):
    def __new__(cls, value=0):
        return super(UInt8Hex, cls).__new__(cls, BitUtils.get_int_with_check(value, bit_count=8, signed=False,
                                                                             base=BitUtils.HEXADECIMAL_BASE))

    def __str__(self):
        return f"{int(self):02x}"

    @staticmethod
    def get_regex() -> str:
        return "[0-9a-fA-F]{2}"


class UInt16Hex(int):
    def __new__(cls, value=0):
        return super(UInt16Hex, cls).__new__(cls, BitUtils.get_int_with_check(value, bit_count=16, signed=False,
                                                                              base=BitUtils.HEXADECIMAL_BASE))

    def __str__(self):
        return f"{int(self):04x}"

    @staticmethod
    def get_regex() -> str:
        return "[0-9a-fA-F]{4}"


class UInt8(int):
    def __new__(cls, value=0):
        return super(UInt8, cls).__new__(cls, BitUtils.get_int_with_check(value, bit_count=8, signed=False,
                                                                          base=BitUtils.DECIMAL_BASE))

    def __str__(self):
        return f"{int(self)}"

    @staticmethod
    def get_regex() -> str:
        # fixme utopia Правильную регулярку должен раздать BitUtils
        return f"[0-9]{{1,{BitUtils.get_digit_count_max(BitUtils.DECIMAL_BASE, bit_count=8)}}}"
