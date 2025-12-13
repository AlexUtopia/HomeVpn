#!/bin/bash

## @brief Функции по установке cpuid
## Приложение позволяет получить информацию по CPU с архитектурой i386/i686/x86_64/ia64
## https://www.etallen.com/cpuid.html


## @brief Установить cpuid
## @retval 0 - успешно
function cpuid_setup() {
    local PACKAGE_NAME="cpuid"
    local DOWNLOAD_URL="https://www.etallen.com/cpuid/cpuid-20250513.src.tar.gz"
    if [[ "${OS_MACHINE_NAME}" == "i386" || "${OS_MACHINE_NAME}" == "i686" || "${OS_MACHINE_NAME}" == "x86_64" || "${OS_MACHINE_NAME}" == "ia64" ]]; then
        local INSTALL_DIR_PATH="${GLOBAL_CONFIG_OPT_DIR_PATH}/${PACKAGE_NAME}"

        local STRIP_COMPONENTS=1
        download_targz_and_unpack "${DOWNLOAD_URL}" "${INSTALL_DIR_PATH}" "remake_dirs" "${STRIP_COMPONENTS}" || return $?

        make -C "${INSTALL_DIR_PATH}" || return $?
        make -C "${INSTALL_DIR_PATH}" DESTDIR="${GLOBAL_CONFIG_ROOT_PATH}" install || return $?
        return 0
    fi
}