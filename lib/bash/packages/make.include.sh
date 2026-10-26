#!/bin/bash

# @file make.include.sh
# @brief Функции работы с make
# @description
# https://www.gnu.org/software/make/
# Требуется для установки/сборки некоторых пакетов проекта


# @description Установить make
# @exitcode 0 успешно
function make_setup() {
    package_manager_install_packages "make" || return $?
    return 0
}