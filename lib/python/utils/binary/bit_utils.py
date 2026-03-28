import re
import sys


class BitUtils:
    DECIMAL_BASE = 10
    HEXADECIMAL_BASE = 16
    OCTAL_BASE = 8
    BINARY_BASE = 2
    TETRAD_IN_BYTE = 2
    BITS_IN_TETRAD = 4
    LSB_TETRAD_MASK = 0x0F
    MSB_TETRAD_MASK = 0xF0
    BITS_IN_BYTE = BITS_IN_TETRAD * TETRAD_IN_BYTE
    UINT8_MIN = 0
    UINT8_MAX = 0xFF
    INT8_MIN = -128
    INT8_MAX = 127
    UINT16_MIN = 0
    UINT16_MAX = 0xFFFF
    INT16_MIN = -32768
    INT16_MAX = 32767
    UINT8_MASK = UINT8_MAX
    UINT16_MASK = UINT16_MAX
    BIT_COUNT_MAX = sys.maxsize.bit_length() + 1
    BASE_DIGIT_LIST = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    BASE_MIN = 2
    BASE_MAX = len(BASE_DIGIT_LIST)
    DIGIT_COUNT_MIN = 1

    @staticmethod
    def is_decimal(val_as_string):
        regex = re.compile(BitUtils.__get_regex_for_check_int(base=BitUtils.DECIMAL_BASE, prefix="(?!0[0-9])"),
                           re.MULTILINE | re.IGNORECASE)
        match = regex.search(val_as_string)
        return match is not None

    @staticmethod
    def is_hexadecimal(val_as_string):
        regex = re.compile(BitUtils.__get_regex_for_check_int(base=BitUtils.HEXADECIMAL_BASE, prefix="0x[0]*"),
                           re.MULTILINE | re.IGNORECASE)
        match = regex.search(val_as_string)
        return match is not None

    @staticmethod
    def is_binary(val_as_string):
        regex = re.compile(BitUtils.__get_regex_for_check_int(base=BitUtils.BINARY_BASE, prefix="0b[0]*"),
                           re.MULTILINE | re.IGNORECASE)
        match = regex.search(val_as_string)
        return match is not None

    @staticmethod
    def is_octal(val_as_string):
        regex = re.compile(BitUtils.__get_regex_for_check_int(base=BitUtils.OCTAL_BASE, prefix="0[0]*"),
                           re.MULTILINE | re.IGNORECASE)
        match = regex.search(val_as_string)
        return match is not None

    @staticmethod
    def __get_regex_for_check_int(base, prefix):
        BitUtils.__check_base(base)
        return fr"^(?>\+|-|){prefix}[{BitUtils.BASE_DIGIT_LIST[0]}-{BitUtils.BASE_DIGIT_LIST[base - 1]}]{{1,{BitUtils.get_digit_count_max(base)}}}$"

    @staticmethod
    def get_int_with_check(val, bit_count=BIT_COUNT_MAX, signed=True, base=DECIMAL_BASE):
        BitUtils.__check_base(base)
        result = 0
        if isinstance(val, str):
            result = int(val, base)
        elif isinstance(val, int):
            result = val
        else:
            raise Exception(f"Value unknown type: {val} | {type(val)}")
        BitUtils.check_int(result, bit_count, signed)
        return result

    @staticmethod
    def get_regex(val_max, base):
        BitUtils.__check_int_type(val_max)
        val_max = abs(val_max)

        val_max_as_str = BitUtils.to_string(val_max, base)
        digit_count = len(val_max_as_str)

        # Заполнение всех digits нулями, пробелами или ничем

        # Правило для первого элемента, последнего элемента, и всех прочих

        # регулярка для val_max = 157, заполнение нулями
        # [0-1](?(?<=1)[0-5]|[0-9])(?(?<=15)[0-6]|[0-9])
        # [1-10](?(?<=1)[0-5]|(?(?<=0)[1-90]|[0-5]))(?(?<=15)[0-6]|[0-9])

        # регулярка для val_max = 157, заполнение пробелами
        # [1-1 ](?(?<=1)[0-5]|(?(?<= )[1-9 ]|[0-5]))(?(?<=15)[0-6]|[0-9])

        # регулярка для val_max = 157, заполнение ничем
        # ограничение по максимальной разрядности
        # [1-1]{0,1}+(?(?<=1)[0-5]|[0-9]){0,1}+(?(?<=15)[0-6]|[0-9])
        # добавляется ревнивая квантификация и оптимизация условия 2.1

        # диапазон 0 до val_max
        #

        # Система счисления запись
        return ""

    @staticmethod
    def check_int(val, bit_count, signed):
        BitUtils.__check_int_type(val)
        val_min = BitUtils.get_int_min_value(bit_count, signed)
        val_max = BitUtils.get_int_max_value(bit_count, signed)
        BitUtils.__check_range(val, val_min, val_max)

    @staticmethod
    def to_string(val, base, to_lower=False):
        BitUtils.__check_int_type(val)
        BitUtils.__check_base(base)
        if val == 0:
            return "0"

        result = ""
        if val < 0:
            result += "-"
            val = abs(val)

        while val > 0:
            result += BitUtils.BASE_DIGIT_LIST[val % base]
            val = val / base
        result = result[::-1]
        if to_lower:
            return result.lower()
        return result

    @staticmethod
    def get_max_by_base(base, digit_count):
        BitUtils.__check_base(base)
        # BitUtils.__check_digit_count(digit_count) # fixme utopia Сделать

        digit_value_max = BitUtils.get_digit_value_max(base)
        result = 0
        while digit_count > 0:
            result = (result * base) + digit_value_max
            digit_count = digit_count - 1
        return result

    @staticmethod
    def get_digit_value_max(base):
        BitUtils.__check_base(base)
        return base - 1

    @staticmethod
    def get_digit_count_max(base, bit_count=BIT_COUNT_MAX):
        BitUtils.__check_base(base)
        int_max = BitUtils.get_int_max_value(bit_count, signed=False)
        # Теоретически может быть -1 (int64 = 0xFFFFFFFFFFFFFFFF), например, для Python2
        return BitUtils.get_digit_count(int_max, base)

    @staticmethod
    def get_digit_count(val, base):
        BitUtils.__check_int_type(val)
        BitUtils.__check_base(base)
        if val == 0:
            return 1
        val = abs(val)

        result = 0
        while val > 0:
            val = val // base
            result = result + 1
        return result

    @staticmethod
    def get_min_by_base(base, digit_count):
        return 0

    @staticmethod
    def get_int_min_max_value(bit_count, signed):
        return BitUtils.get_int_min_value(bit_count, signed), BitUtils.get_int_max_value(bit_count, signed)

    @staticmethod
    def get_int_min_value(bit_count, signed):
        BitUtils.__check_bit_count(bit_count)
        if signed:
            return ~0 << bit_count - 1
        return 0

    @staticmethod
    def get_int_max_value(bit_count, signed):
        BitUtils.__check_bit_count(bit_count)
        if signed:
            return ~(~0 << bit_count - 1)
        return ~(~0 << bit_count)

    @staticmethod
    def __check_bit_count(bit_count):
        BitUtils.__check_int_type(bit_count)
        bit_count_min = 1
        bit_count_max = BitUtils.BIT_COUNT_MAX
        BitUtils.__check_range(bit_count, bit_count_min, bit_count_max)

    @staticmethod
    def __check_base(base):
        BitUtils.__check_int_type(base)
        BitUtils.__check_range(base, BitUtils.BASE_MIN, BitUtils.BASE_MAX)

    @staticmethod
    def __check_int_type(val):
        if not isinstance(val, int):
            raise Exception("Value unknown type, must be int: {}".format(str(val)))

    @staticmethod
    def __check_range(val, val_min, val_max):
        if val_min > val_max:
            raise Exception("Value min ({}) more value max ({}))".format(val_min, val_max))
        if val_min > val > val_max:
            raise Exception("Value invalid range: {}, (min={}, max={})".format(str(val), val_min, val_max))
