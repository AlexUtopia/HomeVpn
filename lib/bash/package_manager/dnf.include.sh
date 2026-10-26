#!/bin/bash

# @file dnf.include.sh
# @brief Функции работы с пакетным менеджером dnf


# @description Обновить установленные пакеты
# @exitcode 0 успешно
function dnf_update_and_upgrade() {
    dnf upgrade -y || return $?
    return 0
}

# @description Установить список пакетов
# Список может состоять из одного пакета
# @arg $1 string Список пакетов
# @exitcode 0 успешно
function dnf_install_packages() {
    local PACKAGE_NAME_LIST="${1}"

    dnf install -y ${PACKAGE_NAME_LIST} || return $?
    return 0
}

# @description Проверить установлен ли пакет
# @arg $1 string Имя пакета
# @exitcode 0 пакет установлен, 1 - нет
function dnf_is_package_installed() {
    local PACKAGE_NAME="${1}"

    dnf list --installed "${PACKAGE_NAME}" &> "/dev/null" || return $?
    return 0
}

# @description Проверить существует (доступен) ли пакет в репозитории пакетов
# @arg $1 string Имя пакета
# @exitcode 0 пакет существует (доступен) в репозитории пакетов, 1 - нет
function dnf_is_package_exists_in_repository() {
    local PACKAGE_NAME="${1}"

    dnf list "${PACKAGE_NAME}" &> "/dev/null" || return $?
    return 0
}