#!/bin/bash

# @file pci.include.sh
# @brief Функции работы с PCI
# @description
# https://eternallybored.org/misc/pciutils/


# @description Установить утилиты работы с PCI
# https://github.com/pciutils/pciutils
# @exitcode 0 успешно
function pci_setup() {
    if is_msys; then
        return 0 # fixme utopia Скачать или собрать пакет
    fi

    package_manager_install_packages "pciutils" || return $?
    return 0
}