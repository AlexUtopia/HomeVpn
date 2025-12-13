#!/bin/bash

## @brief Функции работы с пакетным менеджером pacman


## @brief Обновить установленные пакеты
## @retval 0 - успешно
function pacman_update_and_upgrade() {
    pacman -Syu --noconfirm || return $?
    return 0
}

## @brief Установить список пакетов
## @details Список может состоять из одного пакета
## @param [in] Список пакетов
## @retval 0 - успешно
function pacman_install_packages() {
    local PACKAGE_NAME_LIST="${1}"

    pacman -S --noconfirm ${PACKAGE_NAME_LIST} || return $?
    return 0
}

## @brief Проверить установлен ли пакет
## @param [in] Имя пакета
## @retval 0 - пакет установлен, 1 - нет
function pacman_is_package_installed() {
    local PACKAGE_NAME="${1}"

    pacman -Q "${PACKAGE_NAME}" &> "/dev/null" || return $?
    return 0
}

## @brief Проверить существует (доступен) ли пакет в репозитории пакетов
## @param [in] Имя пакета
## @retval 0 - пакет существует (доступен) в репозитории пакетов, 1 - нет
function pacman_is_package_exists_from_repository() {\
    # fixme utopia команду уточнить https://stackoverflow.com/a/67907522
    local PACKAGE_NAME="${1}"

    pacman -Ss "${PACKAGE_NAME}" &> "/dev/null" || return $?
    return 0
}