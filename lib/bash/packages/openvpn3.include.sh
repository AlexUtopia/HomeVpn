#!/bin/bash

## @brief Функции по установке openvpn3


## @brief Установить openvpn3
## @details https://openvpn.net/cloud-docs/owner/connectors/connector-user-guides/openvpn-3-client-for-linux.html
## @retval 0 - успешно
function openvpn3_setup() {
    if is_termux; then
        return 0
    fi

    if package_manager_is_apt; then
        local OS_DISTRO_VERSION_CODENAME=""
        OS_DISTRO_VERSION_CODENAME=$(get_os_distro_codename_or_version) || return $?

        local PACKAGE_NAME="openvpn3"
        local KEY_FILE_URL="https://packages.openvpn.net/packages-repo.gpg"
        local URIS="https://packages.openvpn.net/openvpn3/debian"
        local SUITES="${OS_DISTRO_VERSION_CODENAME}"
        local COMPONENTS="main"
        local ARCHITECTURES="${APT_MAIN_ARCH}"
        apt_add_sources "${PACKAGE_NAME}" "${KEY_FILE_URL}" "${URIS}" "${SUITES}" "${COMPONENTS}" "${ARCHITECTURES}" || return $?
        package_manager_install_packages "${PACKAGE_NAME}" || return $?
        echo "PACKAGE INSTALLED: \"${PACKAGE_NAME}\", run ${PACKAGE_NAME}"
        return 0
    fi
    return 1
}