#!/bin/bash

## @brief Функции по установке VPN v2rayA
## https://github.com/v2rayA/v2rayA


V2RAYA_PACKAGE_NAME="v2rayA"
V2RAYA_VERSION="2.4.16"


## @brief Получить архитектуру для v2rayA
## @return Архитектура для v2rayA
## @retval 0 - успешно
function v2raya_get_arch() {
    if os_arch_is_x86_64; then
        echo "x64"
        return 0
    elif os_arch_is_x86; then
        echo "x86"
        return 0
    elif os_arch_is_aarch64; then
        echo "arm64"
        return 0
    fi
    return 1
}

## @brief Получить ссылку для скачивания v2rayA
## @details Функция учитывает текущую ОС и её архитектуру (архитектура CPU)
## @return Ссылка для скачивания v2rayA
## @retval 0 - успешно
function v2raya_get_download_url() {
    local OS_ARCH=""
    local OS_DISTR=""
    local PACKAGE_FILE_EXTENSION=""

    OS_ARCH=$(v2raya_get_arch) || return $?

    if is_windows_platform; then
        OS_DISTR="windows_inno"
        PACKAGE_FILE_EXTENSION=".exe"
    else
        PACKAGE_FILE_EXTENSION=$(package_manager_get_file_extension) || return $?
        if package_manager_is_apt; then
            OS_DISTR="debian"
        elif package_manager_is_pacman; then
            OS_DISTR="archlinux"
        elif package_manager_is_dnf || package_manager_is_yum || package_manager_is_zypper; then
            OS_DISTR="redhat"
        else
            return 1
        fi
    fi

    echo "https://github.com/${V2RAYA_PACKAGE_NAME}/${V2RAYA_PACKAGE_NAME}/releases/download/v${V2RAYA_VERSION}/installer_${OS_DISTR}_${OS_ARCH}_${V2RAYA_VERSION}${PACKAGE_FILE_EXTENSION}"
    return 0
}

## @brief Установить пакет v2rayA
## @retval 0 - успешно
function v2raya_packages_setup() {
    if is_termux; then
        return 0
    fi

    local DOWNLOAD_URL=""
    DOWNLOAD_URL=$(v2raya_get_download_url) || return $?

    local TEMP_FILE_PATH=""
    TEMP_FILE_PATH=$(mktemp) &&
    trap_add_remove_temp_path_handler "${TEMP_FILE_PATH}" &&
    download_file "${DOWNLOAD_URL}" "${TEMP_FILE_PATH}" &&
    package_manager_install_package_from_file "${TEMP_FILE_PATH}" || return $?
    return 0
}

## @brief Установить и настроить v2rayA
## @retval 0 - успешно
function v2raya_setup() {
    local SERVICE="v2raya"

    service_disable "${SERVICE}"
    v2raya_packages_setup || return $?
    service_enable "${SERVICE}" || return $?
    if ! service_is_active "${SERVICE}"; then
        echo "FATAL: ${SERVICE} not started"
        return 1
    fi

    return 0
}
