#!/bin/bash

## @brief Функции по установке openvpn(2)


## @brief Установить openvpn(2)
## @details https://community.openvpn.net/openvpn/wiki/OpenvpnSoftwareRepos#DebianUbuntu:UsingOpenVPNaptrepositories
## @retval 0 - успешно
function openvpn_setup() {
    if is_termux || is_msys; then
        return 0
    fi

    if package_manager_is_apt; then
        local OS_DISTRO_VERSION_CODENAME=""
        OS_DISTRO_VERSION_CODENAME=$(get_os_distro_codename_or_version) || return $?

        local PACKAGE_NAME="openvpn"
        local KEY_FILE_URL="https://swupdate.openvpn.net/repos/repo-public.gpg"
        local URIS="https://build.openvpn.net/debian/openvpn/stable"
        local SUITES="${OS_DISTRO_VERSION_CODENAME}"
        local COMPONENTS="main"
        apt_add_sources "${PACKAGE_NAME}" "${KEY_FILE_URL}" "${URIS}" "${SUITES}" "${COMPONENTS}" || return $?
        package_manager_install_packages "${PACKAGE_NAME}" || return $?
        echo "PACKAGE INSTALLED: \"${PACKAGE_NAME}\", run ${PACKAGE_NAME}"
        return 0
    fi

    # fixme utopia Дописать для прочих менеджеров пакетов
    return 1
}