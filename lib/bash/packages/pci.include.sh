#!/bin/bash

## @brief Функции работы с PCI


## @brief Установить утилиты работы с PCI
## @details https://github.com/pciutils/pciutils
## @retval 0 - успешно
function startup_setup() {
    if is_msys; then
        return 0 # fixme utopia Скачать или собрать пакет
    fi

    package_manager_install_packages "pciutils" || return $?
    return 0
}