#!/bin/bash

# @file package_manager.include.sh
# @brief Функции работы с системным менеджером пакетов

# fixme utopia Добавить для винды

source "${HOME_VPN_PROJECT_ROOT}/lib/bash/package_manager/apt.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/package_manager/dnf.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/package_manager/pacman.include.sh"


# @description Проверить существует ли пакетный менеджер apt
# Debian, Ubuntu, Linux Mint, termux
# @exitcode 0 пакетный менеджер apt существует
# @exitcode 1 не существует
function package_manager_is_apt() {
    is_executable_available "apt" || return $?
    return 0
}

# @description Проверить существует ли пакетный менеджер pacman
# Arch Linux, MSYS2
# @exitcode 0 пакетный менеджер pacman существует
# @exitcode 1 не существует
function package_manager_is_pacman() {
    is_executable_available "pacman" || return $?
    return 0
}

# @description Проверить существует ли пакетный менеджер yum
# RHEL, Fedora, CentOS
# @exitcode 0 пакетный менеджер yum существует
# @exitcode 1 не существует
function package_manager_is_yum() {
    is_executable_available "yum" || return $?
    return 0
}

# @description Проверить существует ли пакетный менеджер dnf
# Fedora
# @exitcode 0 пакетный менеджер dnf существует
# @exitcode 1 не существует
function package_manager_is_dnf() {
    is_executable_available "dnf" || return $?
    return 0
}

# @description Проверить существует ли пакетный менеджер zypper
# openSUSE
# @exitcode 0 пакетный менеджер zypper существует
# @exitcode 1 не существует
function package_manager_is_zypper() {
    is_executable_available "zypper" || return $?
    return 0
}

# @description Обновить установленные пакеты
# @exitcode 0 успешно
function package_manager_update_and_upgrade() {
    if package_manager_is_apt; then
        apt_update_and_upgrade || return $?
    elif package_manager_is_pacman; then
        pacman_update_and_upgrade || return $?
    elif package_manager_is_dnf; then
        dnf_update_and_upgrade || return $?
    elif package_manager_is_yum; then
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

# @description Установить список пакетов
# Список может состоять из одного пакета
# @arg $1 string Список пакетов
# @exitcode 0 успешно
function package_manager_install_packages() {
    local PACKAGE_NAME_LIST="${1}"

    if package_manager_is_apt; then
        apt_install_packages "${PACKAGE_NAME_LIST}" || return $?
    elif package_manager_is_pacman; then
        pacman_install_packages "${PACKAGE_NAME_LIST}" || return $?
    elif package_manager_is_dnf; then
        dnf_install_packages "${PACKAGE_NAME_LIST}" || return $?
    elif package_manager_is_yum; then
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
    elif package_manager_is_dnf; then
        dnf_is_package_installed "${PACKAGE_NAME}" || return $?
    elif package_manager_is_yum; then
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
    elif package_manager_is_dnf; then
        dnf_is_package_exists_in_repository "${PACKAGE_NAME}" || return $?
    elif package_manager_is_yum; then
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


function package_manager_install_package_from_file() {
    local PACKAGE_INSTALLER_FILE_PATH="${1}"

    if package_manager_is_apt; then
        apt_package_manager_install_package_from_file "${PACKAGE_INSTALLER_FILE_PATH}" || return $?
    elif package_manager_is_pacman; then
        pacman_package_manager_install_package_from_file "${PACKAGE_INSTALLER_FILE_PATH}" || return $?
    elif package_manager_is_dnf; then
        dnf_package_manager_install_package_from_file "${PACKAGE_INSTALLER_FILE_PATH}" || return $?
    elif package_manager_is_yum; then
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


function package_manager_get_file_extension() {
    if package_manager_is_apt; then
        echo ".deb"
        return 0
    elif package_manager_is_pacman; then
        echo ".pkg.tar.zst"
        return 0
    elif package_manager_is_dnf; then
        echo ".rpm"
        return 0
    elif package_manager_is_yum; then
        echo ".rpm"
        return 0
    elif package_manager_is_zypper; then
        echo ".rpm"
        return 0
    else
        echo "FATAL: unknown package manager"
        return 1
    fi
    return 0
}