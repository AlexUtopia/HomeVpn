#!/bin/bash

## @brief Функции работы со вспомогательными пакетами разработчика проекта


## @brief Установить вспомогательными пакеты разработчика проекта
## @details Утилиты nano, htop, kvm-ok, lsusb, lshw
## @retval 0 - успешно
function dev_packages_setup() {
    if is_msys; then
        return 0
    fi

    local PACKAGE_LIST="nano htop cpu-checker usbutils lshw"
    if is_termux; then
        PACKAGE_LIST="nano htop usbutils"
    fi

    package_manager_install_packages "${PACKAGE_LIST}" || return $?
    return 0
}