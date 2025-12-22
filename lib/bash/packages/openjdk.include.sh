#!/bin/bash

## @brief Функции по установке openjdk
## @details Открытая реализация Java платформы
## https://openjdk.org/


## @brief Установить openjdk
## @retval 0 - успешно
function openjdk_setup() {
    if is_msys; then # Скачаем и установим приложение вручную
        return 0
    fi

    local OPENJDK_PACKAGE_SUFFIX="-jdk"
    if is_termux; then
        OPENJDK_PACKAGE_SUFFIX=""
    fi

    package_manager_install_packages "openjdk-21${OPENJDK_PACKAGE_SUFFIX}" || \
    package_manager_install_packages "openjdk-19${OPENJDK_PACKAGE_SUFFIX}" || \
    package_manager_install_packages "openjdk-17${OPENJDK_PACKAGE_SUFFIX}" || return $?
    return 0
}