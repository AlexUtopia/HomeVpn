#!/bin/bash

## @brief Функции работы с make
## https://www.gnu.org/software/make/
## @details Требуется для установки/сборки некоторых пакетов проекта


## @brief Установить make
## @retval 0 - успешно
function make_setup() {
    package_manager_install_packages "make" || return $?
    return 0
}