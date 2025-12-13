#!/bin/bash

## @brief Функции по установке pycharm
## @details IDE для разработки на python
## https://www.jetbrains.com/pycharm/


## @brief Установить pycharm
## @retval 0 - успешно
function pycharm_setup() {
    local PACKAGE_NAME="pycharm-community-2025.1.3.1"
    local DOWNLOAD_URL="https://download.jetbrains.com/python/${PACKAGE_NAME}.tar.gz"
    local INSTALL_DIR_PATH="${GLOBAL_CONFIG_OPT_DIR_PATH}"
    local PYCHARM_INSTALL_DIR_PATH="${INSTALL_DIR_PATH}/${PACKAGE_NAME}"

    if [[ -d "${PYCHARM_INSTALL_DIR_PATH}" ]]; then
        echo "WARNING: Pycharm \"${PACKAGE_NAME}\" already installed"
        return 0
    fi

    openjdk_setup || return $?

    download_targz_and_unpack "${DOWNLOAD_URL}" "${INSTALL_DIR_PATH}" || return $?
    return 0
}