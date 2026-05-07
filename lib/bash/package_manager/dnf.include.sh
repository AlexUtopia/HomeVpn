#!/bin/bash

## @brief Функции работы с пакетным менеджером dnf


## @brief Обновить установленные пакеты
## @retval 0 - успешно
function dnf_update_and_upgrade() {
    dnf upgrade -y || return $?
    return 0
}

## @brief Установить список пакетов
## @details Список может состоять из одного пакета
## @param [in] Список пакетов
## @retval 0 - успешно
function dnf_install_packages() {
    local PACKAGE_NAME_LIST="${1}"

    dnf install -y ${PACKAGE_NAME_LIST} || return $?
    return 0
}

## @brief Проверить установлен ли пакет
## @param [in] Имя пакета
## @retval 0 - пакет установлен, 1 - нет
function dnf_is_package_installed() {
    local PACKAGE_NAME="${1}"

    dnf list --installed "${PACKAGE_NAME}" &> "/dev/null" || return $?
    return 0
}

## @brief Проверить существует (доступен) ли пакет в репозитории пакетов
## @param [in] Имя пакета
## @retval 0 - пакет существует (доступен) в репозитории пакетов, 1 - нет
function dnf_is_package_exists_in_repository() {
    local PACKAGE_NAME="${1}"

    dnf list "${PACKAGE_NAME}" &> "/dev/null" || return $?
    return 0
}