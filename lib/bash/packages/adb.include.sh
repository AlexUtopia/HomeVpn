#!/bin/bash

## @brief Функции работы с Android SDK platform-tools (пакет включает в себя adb)
## https://developer.android.com/tools/releases/platform-tools


## @brief Получить платформу для Android SDK platform-tools
## @details Только для ОС с архитектурой x86_64
## @return Платформа для Android SDK platform-tools
## @retval 0 - успешно
function android_sdk_platform_tools_get_platform() {
    if ! os_arch_is_x86_64; then
        return 1
    fi

    if is_linux; then
        echo "linux"
        return 0
    elif is_windows_platform; then
        echo "windows"
        return 0
    fi
    echo "[android_sdk_platform_tools] UNSUPPORTED PLATFORM/ARCH"
    return 1
}

## @brief Установить последний Android SDK platform-tools (пакет включает в себя adb)
## @details https://developer.android.com/tools/releases/platform-tools
## @retval 0 - успешно
function android_sdk_platform_tools_setup_latest() {
    local ANDROID_SDK_PLATFORM_TOOLS_PLATFORM=""
    ANDROID_SDK_PLATFORM_TOOLS_PLATFORM=$(android_sdk_platform_tools_get_platform) || return $?

    local PACKAGE_NAME="android-sdk-platform-tools"
    local DOWNLOAD_URL="https://dl.google.com/android/repository/platform-tools-latest-${ANDROID_SDK_PLATFORM_TOOLS_PLATFORM}.zip"
    local INSTALL_DIR_PATH="${GLOBAL_CONFIG_OPT_DIR_PATH}/${PACKAGE_NAME}"

    local STRIP_COMPONENTS=1
    download_zip_and_unpack "${DOWNLOAD_URL}" "${INSTALL_DIR_PATH}" "remake_dirs" "${STRIP_COMPONENTS}" || return $?
    return 0
}

## @brief Установить системный Android SDK platform-tools (пакет включает в себя adb)
## @details Android/termux: android-tools
##          Ubuntu:         android-sdk-platform-tools
## @retval 0 - успешно
function android_sdk_platform_tools_setup_default() {
    if is_termux; then
        package_manager_install_packages "android-tools" || return $?
        return 0
    elif is_linux; then
        package_manager_install_packages "android-sdk-platform-tools" || return $?
        return 0
    elif is_msys; then
        package_manager_install_packages "${GLOBAL_CONFIG_MSYS2_PACKAGE_PREFIX}android-tools" || return $?
        return 0
    fi
    return 1
}

## @brief Установить Android SDK platform-tools (пакет включает в себя adb)
## @retval 0 - успешно
function android_sdk_platform_tools_setup() {
    android_sdk_platform_tools_setup_latest || android_sdk_platform_tools_setup_default || return $?
    return 0
}
