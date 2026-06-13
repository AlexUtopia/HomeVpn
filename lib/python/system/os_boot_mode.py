import typing

class OsBootMode(typing.Protocol):

    def is_bios_boot(self) -> bool:
        ...

    def is_uefi_boot(self) -> bool:
        ...

    def is_secure_boot(self) -> bool:
        ...

    def get_bios_boot_platform_list(self) -> list[str]:
        ...

    def get_uefi_boot_platform_list(self) -> list[str]:
        ...

    def get_secure_boot_platform_list(self) -> list[str]:
        ...
