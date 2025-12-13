#!/bin/bash

## @brief Функции по установке RDP клиента
## @details Клиент удалённого управления ОС Windows (по протоколу RPD)
## https://www.freerdp.com/


## @brief Установить умолчательный RPD клиент
## @details Умолчательный - тот который предоставляется системным менеджером пакетов
## @retval 0 - успешно
function rdp_client_setup_default() {
    local RDP_CLIENT_PACKAGE="freerdp2-x11 freerdp2-wayland"
    if is_termux; then
        RDP_CLIENT_PACKAGE="freerdp"
    elif is_msys; then
        RDP_CLIENT_PACKAGE="${GLOBAL_CONFIG_MSYS2_PACKAGE_PREFIX}freerdp"
    fi

    package_manager_install_packages "${RDP_CLIENT_PACKAGE}" || return $?
    return 0
}

## @brief Установить "nightly" сборку RPD клиента
## @retval 0 - успешно
function rdp_client_setup_nightly() {
    if package_manager_is_apt; then
        local OS_DISTRO_VERSION_CODENAME=""
        OS_DISTRO_VERSION_CODENAME=$(get_os_distro_codename_or_version) || return $?

        local PACKAGE_NAME="freerdp-nightly"
        local KEY_FILE_URL="http://pub.freerdp.com/repositories/ADD6BF6D97CE5D8D.asc"
        local URIS="http://pub.freerdp.com/repositories/deb/${OS_DISTRO_VERSION_CODENAME}"
        local SUITES="${PACKAGE_NAME}"
        local COMPONENTS="main"
        apt_add_sources "${PACKAGE_NAME}" "${KEY_FILE_URL}" "${URIS}" "${SUITES}" "${COMPONENTS}" || return $?
        package_manager_install_packages "${PACKAGE_NAME}" || return $?
        echo "PACKAGE INSTALLED: \"${PACKAGE_NAME}\", run /opt/freerdp-nightly/bin/xfreerdp"
        return 0
    fi
    return 1
}

## @brief Установить RPD клиент
## @retval 0 - успешно
function rdp_client_setup() {
    if is_termux || is_msys; then
        rdp_client_setup_default || return $?
    else
        rdp_client_setup_nightly || rdp_client_setup_default || return $? # fixme utopia Чтобы будем делать с Linux ARM?
    fi
    return 0
}