import enum


# fixme utopia Add unit tests
class PciPassthroughMode(enum.Enum):
    ## Не пробрасывать PCI устройства
    NONE = 0

    ## Пробросить только указанные PCI устройства
    DEFAULT = 1

    ## Пробросить устройства которые не входят в IOMMU группы с непробрасываемыми устройствами
    FLEX = 2

    ## Пробросить все устройства IOMMU групп куда входят целевые PCI устройства
    # @warning Использовать с особой осторожностью и пониманием дела
    FORCE = 3

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)

    @staticmethod
    def argparse(s):
        try:
            return PciPassthroughMode[s.strip().upper()]
        except KeyError:
            return s

    def __bool__(self):
        return not self.is_none()

    def is_none(self):
        return self == PciPassthroughMode.NONE

    def is_default(self):
        return self == PciPassthroughMode.DEFAULT

    def is_flex(self):
        return self == PciPassthroughMode.FLEX

    def is_force(self):
        return self == PciPassthroughMode.FORCE

    @staticmethod
    def get_help(indent_spaces_count=1):
        indent = " " * int(indent_spaces_count)
        result = ""
        result += f"{indent}   {PciPassthroughMode.NONE} - PCI device(s) not passthrough\n"
        result += f"{indent}{PciPassthroughMode.DEFAULT} - Passthrough only target PCI device(s) if possible\n"
        result += f"{indent}   {PciPassthroughMode.FLEX} - Passthrough only those PCI device(s) that can be passthroughed\n"
        result += f"{indent}  {PciPassthroughMode.FORCE} - Passthrough all devices of IOMMU groups that include target PCI device(s)"
        return result
