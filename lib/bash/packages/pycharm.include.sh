#!/bin/bash

## @brief Функции по установке pycharm
## @details IDE для разработки на python
## https://www.jetbrains.com/pycharm/


## @brief Установить pycharm
## @retval 0 - успешно
function pycharm_setup() {
    local PYCHARM="pycharm-community-2025.1.3.1"
    local DOWNLOAD_URL="https://download.jetbrains.com/python/${PYCHARM}.tar.gz"
    local INSTALL_DIR_PATH="${GLOBAL_CONFIG_ROOT_PATH}/opt"
    local PYCHARM_INSTALL_DIRECTORY="${INSTALL_DIR_PATH}/${PYCHARM}"

    if [[ -d "${PYCHARM_INSTALL_DIRECTORY}" ]]; then
        echo "WARNING: Pycharm \"${PYCHARM}\" already installed"
        return 0
    fi

    openjdk_setup || return $?

    download_targz_and_unpack "${DOWNLOAD_URL}" "${INSTALL_DIR_PATH}" || return $?
    return 0
}