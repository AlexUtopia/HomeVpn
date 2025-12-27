#!/bin/bash

## @brief Функции работы с qemu
## https://www.qemu.org/
## https://gitlab.com/qemu-project/qemu

# fixme utopia Перенести сюда скрипт сборки qemu


## @brief Установить qemu
## @retval 0 - успешно
function qemu_setup() {
    local PACKAGE_LIST="qemu-system swtpm"
    if is_termux; then
        PACKAGE_LIST="qemu-system-x86-64 swtpm"
    elif is_msys; then
        PACKAGE_LIST="${GLOBAL_CONFIG_MSYS2_PACKAGE_PREFIX}qemu"
    fi

    package_manager_install_packages "${PACKAGE_LIST}" || return $?
    return 0
}