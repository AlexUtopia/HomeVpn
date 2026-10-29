"""Режимы проброса PCI устройств."""

import enum


# NB: add unit tests
class PciPassthroughMode(enum.Enum):
    """Режим проброса PCI устройств в виртуальную машину"""

    ## Не пробрасывать PCI устройства
    NONE = 0

    ## Пробросить только указанные PCI устройства
    DEFAULT = 1

    ## Пробросить устройства которые не входят в IOMMU группы с непробрасываемыми устройствами
    FLEX = 2

    ## Пробросить все устройства IOMMU групп куда входят целевые PCI устройства
    # @warning Использовать с особой осторожностью и пониманием дела
    FORCE = 3

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return str(self)

    @staticmethod
    def argparse(s: str) -> "PciPassthroughMode | str":
        """Разобрать режим из аргумента командной строки

        :param s: Строка с именем режима
        :return: Режим или исходная строка, если режим неизвестен
        """
        try:
            return PciPassthroughMode[s.strip().upper()]
        except KeyError:
            return s

    def __bool__(self) -> bool:
        return not self.is_none()

    def is_none(self) -> bool:
        """Проверить режим ``NONE``

        :return: ``True`` — устройства не пробрасываются
        """
        return self == PciPassthroughMode.NONE

    def is_default(self) -> bool:
        """Проверить режим ``DEFAULT``

        :return: ``True`` — пробрасываются только целевые устройства
        """
        return self == PciPassthroughMode.DEFAULT

    def is_flex(self) -> bool:
        """Проверить режим ``FLEX``

        :return: ``True`` — пробрасываются устройства, которые можно пробросить
        """
        return self == PciPassthroughMode.FLEX

    def is_force(self) -> bool:
        """Проверить режим ``FORCE``

        :return: ``True`` — пробрасываются все устройства IOMMU групп
        """
        return self == PciPassthroughMode.FORCE

    @staticmethod
    def get_help(indent_spaces_count: int = 1) -> str:
        """Получить справку по режимам проброса

        :param indent_spaces_count: Количество пробелов в начале строк
        :return: Текст справки
        """
        indent = " " * int(indent_spaces_count)
        result = ""
        result += f"{indent}   {PciPassthroughMode.NONE} - PCI device(s) not passthrough\n"
        result += f"{indent}{PciPassthroughMode.DEFAULT} - Passthrough only target PCI device(s) if possible\n"
        result += (f"{indent}{PciPassthroughMode.FLEX} - Passthrough only those PCI device(s) that can be "
                   f"passthroughed\n")
        result += (f"{indent}  {PciPassthroughMode.FORCE} - Passthrough all devices of IOMMU groups that include "
                   f"target PCI device(s)")
        return result
