#!/bin/bash

## @brief Функции по установке и работе с nodejs
## Требуется для работы плагина Roo code для pycharm IDE


NODEJS_VERSION="24.x"

## @brief Установить пакет nodejs
## @details https://nodejs.org/en/download
## @details https://ruvds.com/ru/helpcenter/kak-ustanovit-nodejs/
## @retval 0 - успешно
function nodejs_packages_setup() {
    if package_manager_is_apt; then
        local PACKAGE_NAME="nodejs"
        local KEY_FILE_URL="https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key"
        local URIS="https://deb.nodesource.com/node_${NODEJS_VERSION}"
        local SUITES="nodistro"
        local COMPONENTS="main"
        apt_add_sources "${PACKAGE_NAME}" "${KEY_FILE_URL}" "${URIS}" "${SUITES}" "${COMPONENTS}" || return $?
        package_manager_install_packages "${PACKAGE_NAME}" || return $?
        echo "PACKAGE INSTALLED: \"${PACKAGE_NAME}\", run ${PACKAGE_NAME}"
        return 0
    fi
    return 1
}