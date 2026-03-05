#!/bin/bash

## @brief Функции работы с Android platform-tools (пакет включает в себя adb)
## https://developer.android.com/tools/releases/platform-tools


## @brief Получить платформу для Android platform-tools
## @return Платформа для Android platform-tools
## @retval 0 - успешно
function android_platform_tools_get_platform() {
    if is_linux; then
        echo "linux"
        return 0
    elif is_windows_platform; then
        echo "windows"
        return 0
    fi
    echo "[android_platform_tools] UNSUPPORTED PLATFORM/ARCH"
    return 1
}

## @brief Установить последний Android platform-tools (пакет включает в себя adb)
## @details https://developer.android.com/tools/releases/platform-tools
## @retval 0 - успешно
function android_platform_tools_setup_latest() {
    if ! os_arch_is_x86_64; then
        return 1
    fi

    local ANDROID_PLATFORM_TOOLS_PLATFORM=""
    ANDROID_PLATFORM_TOOLS_PLATFORM=$(android_platform_tools_get_platform) || return $?

    local PACKAGE_NAME="android-platform-tools"
    local DOWNLOAD_URL="https://dl.google.com/android/repository/platform-tools-latest-${ANDROID_PLATFORM_TOOLS_PLATFORM}.zip"
    local INSTALL_DIR_PATH="${GLOBAL_CONFIG_OPT_DIR_PATH}/${PACKAGE_NAME}"

    local STRIP_COMPONENTS=1
    download_zip_and_unpack "${DOWNLOAD_URL}" "${INSTALL_DIR_PATH}" "remake_dirs" "${STRIP_COMPONENTS}" || return $?
    return 0
}
