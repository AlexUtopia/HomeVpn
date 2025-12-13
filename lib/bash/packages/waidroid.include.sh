#!/bin/bash

## @brief Функции по установке waydroid
## https://repo.waydro.id/


## @brief Установить waydroid
## @details https://docs.waydro.id/usage/install-on-desktops#ubuntu-debian-and-derivatives
## @details https://learn.microsoft.com/en-us/windows/android/wsa/
## @retval 0 - успешно
function waydroid_setup() {
    if is_termux || is_msys; then
        return 0
    fi

    if package_manager_is_apt; then
        local OS_DISTRO_VERSION_CODENAME=""
        OS_DISTRO_VERSION_CODENAME=$(get_os_distro_codename_or_version) || return $?

        local PACKAGE_NAME="waydroid"
        local KEY_FILE_URL="https://repo.waydro.id/waydroid.gpg"
        local URIS="https://repo.waydro.id"
        local SUITES="${OS_DISTRO_VERSION_CODENAME}"
        local COMPONENTS="main"
        apt_add_sources "${PACKAGE_NAME}" "${KEY_FILE_URL}" "${URIS}" "${SUITES}" "${COMPONENTS}" || return $?
        package_manager_install_packages "${PACKAGE_NAME}" || return $?
        echo "PACKAGE INSTALLED: \"${PACKAGE_NAME}\", run ${PACKAGE_NAME}"
        return 0
    fi
    return 1
}