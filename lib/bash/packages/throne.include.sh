#!/bin/bash

# @file throne.include.sh
# @brief Функции по установке VPN Throne
# @description
# https://github.com/throneproj/Throne


THRONE_PACKAGE_NAME="Throne"
THRONE_VERSION="1.3.0-beta.3"


# @description Получить ссылку для скачивания Throne
# @stdout Ссылка для скачивания Throne
# @exitcode 0 успешно
function throne_get_download_url() {
    echo "https://raw.githubusercontent.com/throneproj/${THRONE_PACKAGE_NAME}/refs/tags/${THRONE_VERSION}/script/install_linux.py"
    return 0
}

# @description Установить и настроить Throne
# @exitcode 0 успешно
function throne_setup() {
    if ! is_linux; then
        return 0
    fi

    local DOWNLOAD_URL=""
    DOWNLOAD_URL=$(throne_get_download_url) || return $?

    local PYTHON_EXECUTABLE=""
    PYTHON_EXECUTABLE="$(python_get_executable)" || return $?

    download_file "${DOWNLOAD_URL}" "-" | "${PYTHON_EXECUTABLE}" || return $?
    return 0
}