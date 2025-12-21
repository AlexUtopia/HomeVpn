#!/bin/bash

## @brief Функции работы с системным менеджером пакетов


## @brief Проверить существует ли пакетный менеджер apt
## @details Debian, Ubuntu, Linux Mint, termux
## @retval 0 - пакетный менеджер apt существует; 1 - не существует
function package_manager_is_apt() {
    is_executable_available "apt" || return $?
    return 0
}

## @brief Проверить существует ли пакетный менеджер pacman
## @details Arch Linux, MSYS2
## @retval 0 - пакетный менеджер pacman существует; 1 - не существует
function package_manager_is_pacman() {
    is_executable_available "pacman" || return $?
    return 0
}

## @brief Проверить существует ли пакетный менеджер yum
## @details RHEL, Fedora, CentOS
## @retval 0 - пакетный менеджер yum существует; 1 - не существует
function package_manager_is_yum() {
    is_executable_available "yum" || return $?
    return 0
}

## @brief Проверить существует ли пакетный менеджер dnf
## @details Fedora
## @retval 0 - пакетный менеджер dnf существует; 1 - не существует
function package_manager_is_dnf() {
    is_executable_available "dnf" || return $?
    return 0
}

## @brief Проверить существует ли пакетный менеджер zypper
## @details openSUSE
## @retval 0 - пакетный менеджер zypper существует; 1 - не существует
function package_manager_is_zypper() {
    is_executable_available "zypper" || return $?
    return 0
}

## @brief Обновить установленные пакеты
## @retval 0 - успешно
function package_manager_update_and_upgrade() {
    if package_manager_is_apt; then
        apt_update_and_upgrade || return $?
    elif package_manager_is_pacman; then
        pacman_update_and_upgrade || return $?
    elif package_manager_is_yum; then
        # fixme utopia Дописать
        return 1
    elif package_manager_is_dnf; then
        # fixme utopia Дописать
        return 1
    elif package_manager_is_zypper; then
        # fixme utopia Дописать
        return 1
    else
        echo "FATAL: unknown package manager"
        return 1
    fi
    return 0
}

## @brief Установить список пакетов
## @details Список может состоять из одного пакета
## @param [in] Список пакетов
## @retval 0 - успешно
function package_manager_install_packages() {
    local PACKAGE_NAME_LIST="${1}"

    if package_manager_is_apt; then
        apt_install_packages "${PACKAGE_NAME_LIST}" || return $?
    elif package_manager_is_pacman; then
        pacman_install_packages "${PACKAGE_NAME_LIST}" || return $?
    elif package_manager_is_yum; then
        # fixme utopia Дописать
        return 1
    elif package_manager_is_dnf; then
        # fixme utopia Дописать
        return 1
    elif package_manager_is_zypper; then
        # fixme utopia Дописать
        return 1
    else
        echo "FATAL: unknown package manager"
        return 1
    fi
    return 0
}

function package_manager_is_package_installed() {
    local PACKAGE_NAME="${1}"

    if package_manager_is_apt; then
        apt_is_package_installed "${PACKAGE_NAME}" || return $?
    elif package_manager_is_pacman; then
        pacman_is_package_installed "${PACKAGE_NAME}" || return $?
    elif package_manager_is_yum; then
        # fixme utopia Дописать
        return 1
    elif package_manager_is_dnf; then
        # fixme utopia Дописать
        return 1
    elif package_manager_is_zypper; then
        # fixme utopia Дописать
        return 1
    else
        echo "FATAL: unknown package manager"
        return 1
    fi
    return 0
}

function package_manager_is_package_exists_in_repository() {
    local PACKAGE_NAME="${1}"

    if package_manager_is_apt; then
        apt_is_package_exists_in_repository "${PACKAGE_NAME}" || return $?
    elif package_manager_is_pacman; then
        pacman_is_package_exists_in_repository "${PACKAGE_NAME}" || return $?
    elif package_manager_is_yum; then
        # fixme utopia Дописать
        return 1
    elif package_manager_is_dnf; then
        # fixme utopia Дописать
        return 1
    elif package_manager_is_zypper; then
        # fixme utopia Дописать
        return 1
    else
        echo "FATAL: unknown package manager"
        return 1
    fi
    return 0
}