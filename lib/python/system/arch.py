from __future__ import annotations

import cpuinfo


class Arch:
    ARCH_X86_64 = "X86_64"
    ARCH_X86_32 = "X86_32"
    ARCH_ARM_8 = "ARM_8"
    ARCH_ARM_7 = "ARM_7"
    ARCH_PPC_32 = "PPC_32"
    ARCH_PPC_64 = "PPC_64"
    ARCH_SPARC_32 = "SPARC_32"
    ARCH_SPARC_64 = "SPARC_64"
    ARCH_S390X = "S390X"
    ARCH_MIPS_32 = "MIPS_32"
    ARCH_MIPS_64 = "MIPS_64"
    ARCH_RISCV_32 = "RISCV_32"
    ARCH_RISCV_64 = "RISCV_64"
    ARCH_UNKNOWN = "unknown"

    TABLE = {
        (ARCH_X86_64, 64): {"name": "x86_64", "compat": {(ARCH_X86_32, 32)}},
        (ARCH_X86_32, 32): {"name": "i386"},

        (ARCH_ARM_8, 64): {"name": "aarch64", "compat": {(ARCH_ARM_8, 32), (ARCH_ARM_7, 32)}},
        (ARCH_ARM_8, 32): {"name": "arm", "compat": {(ARCH_ARM_7, 32)}},
        (ARCH_ARM_7, 32): {"name": "arm"},

        (ARCH_PPC_64, 64): {"name": "ppc64"},
        (ARCH_PPC_32, 32): {"name": "ppc"},

        (ARCH_SPARC_64, 64): {"name": "sparc64"},
        (ARCH_SPARC_32, 32): {"name": "sparc"},

        (ARCH_S390X, 64): {"name": "s390x"},

        (ARCH_MIPS_64, 64): {"name": "mips64"},
        (ARCH_MIPS_32, 32): {"name": "mips"},

        (ARCH_RISCV_64, 64): {"name": "riscv64"},
        (ARCH_RISCV_32, 32): {"name": "riscv32"}
    }

    def __init__(self, arch: str | Arch | None = None):
        if isinstance(arch, Arch):
            self.__arch: str = arch.__arch
            self.__bits: int = arch.__bits
        else:
            if arch:
                _arch, _bits = Arch.__parse_arch(arch)
                if not _arch or not _bits:
                    raise Exception(f"[Arch] Unknown ({arch})")
                self.__arch: str = _arch
                self.__bits: int = _bits
            else:
                my_cpu_info = cpuinfo.get_cpu_info()
                self.__arch: str = my_cpu_info["arch"]
                self.__bits: int = my_cpu_info["bits"]

    def __str__(self) -> str:
        return self.TABLE.get(self.get_as_tuple(), dict()).get("name", self.ARCH_UNKNOWN)

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other: Arch) -> bool:
        if other is self:
            return True
        return self.get_as_tuple() == other.get_as_tuple()

    def __hash__(self) -> int:
        return hash(self.get_as_tuple())

    def get_as_tuple(self) -> tuple[str, int]:
        return self.__arch, self.__bits

    def is_x86_compat(self) -> bool:
        return self.__arch in {self.ARCH_X86_64, self.ARCH_X86_32}

    def is_arm_compat(self) -> bool:
        return self.__arch in {self.ARCH_ARM_7, self.ARCH_ARM_8}

    ## Проверить что текущая архитектура ОС является целевой
    # @details Допустимые значения arch_for_check можно увидеть здесь
    #          https://github.com/workhorsy/py-cpuinfo/blob/master/cpuinfo/cpuinfo.py#L782
    # @details Полезные ссылки на тему
    #          https://unix.stackexchange.com/questions/136959/where-does-uname-get-its-information-from
    #          https://habr.com/ru/companies/intel/articles/201462/
    #          https://stackoverflow.com/questions/45125516/possible-values-for-uname-m
    #          https://github.com/torvalds/linux/blob/master/scripts/package/mkdebian#L21
    #          http://ports.ubuntu.com/ubuntu-ports/dists/noble/main/
    #          http://archive.ubuntu.com/ubuntu/dists/noble/main/
    #          https://youtu.be/6DybX5Lkqt4?si=jocEAhC03jxshFLQ
    # @details В настоящий момент сделано по-простому - с использованием библиотеки cpuinfo
    # @param [in] os_for_check Целевая архитектура ОС
    # @return True - текущая архитектура ОС является целевой; False - нет
    def check(self, arch_for_check: str | Arch) -> bool:
        return self == Arch(arch_for_check)

    def is_compat(self, arch_for_check: str | Arch) -> bool:
        # https://share.google/aimode/wM8wksl3Zcs0nRA9o
        # | qemu-system (после двоеточия архитектура elf qemu-system) | host arch | Можно использовать KVM |
        # | --------------------------------------------------------- | --------- | ---------------------- |
        # | qemu-system-i386:i386                                     | x86_64    | +                      |
        # | qemu-system-i386:i386                                     | i386      | +                      |
        # | qemu-system-i386:x86_64                                   | x86_64    | +                      |
        # | qemu-system-i386:x86_64                                   | i386      | не запустится          |
        # | qemu-system-x86_64:i386                                   | x86_64    | -                      |
        # | qemu-system-x86_64:i386                                   | i386      | -                      |
        # | qemu-system-x86_64:x86_64                                 | x86_64    | +                      |
        # | qemu-system-x86_64:x86_64                                 | i386      | не запустится          |
        # fixme utopia Метод не учитывает архитектуру целевого приложения

        target_arch = Arch(arch_for_check)
        if self == target_arch:
            return True

        return target_arch.get_as_tuple() in self.TABLE.get(self.get_as_tuple(), dict()).get("compat", set())

    @staticmethod
    def __parse_arch(arch_for_check: str) -> tuple[str | None, int | None]:
        if arch_for_check == "arm":
            return Arch.ARCH_ARM_7, 32
        return cpuinfo.cpuinfo._parse_arch(arch_for_check)
