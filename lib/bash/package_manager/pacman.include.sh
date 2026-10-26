#!/bin/bash

# @file pacman.include.sh
# @brief Функции работы с пакетным менеджером pacman


# @description Обновить установленные пакеты
# @exitcode 0 успешно
function pacman_update_and_upgrade() {
    pacman -Syu --noconfirm || return $?
    return 0
}

# @description Установить список пакетов
# Список может состоять из одного пакета
# @arg $1 string Список пакетов
# @exitcode 0 успешно
function pacman_install_packages() {
    local PACKAGE_NAME_LIST="${1}"

    pacman -S --noconfirm ${PACKAGE_NAME_LIST} || return $?
    return 0
}

# @description Проверить установлен ли пакет
# @arg $1 string Имя пакета
# @exitcode 0 пакет установлен, 1 - нет
function pacman_is_package_installed() {
    local PACKAGE_NAME="${1}"

    pacman -Q "${PACKAGE_NAME}" &> "/dev/null" || return $?
    return 0
}

# @description Проверить существует (доступен) ли пакет в репозитории пакетов
# @arg $1 string Имя пакета
# @exitcode 0 пакет существует (доступен) в репозитории пакетов, 1 - нет
function pacman_is_package_exists_in_repository() {
    # fixme utopia команду уточнить https://stackoverflow.com/a/67907522
    local PACKAGE_NAME="${1}"

    pacman -Ss "${PACKAGE_NAME}" &> "/dev/null" || return $?
    return 0
}