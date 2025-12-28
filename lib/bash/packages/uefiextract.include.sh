#!/bin/bash

## @brief Функции работы с uefiextract
## https://github.com/LongSoft/UEFITool


## @brief Получить платформу для uefiextract
## @return Платформа для uefiextract
## @retval 0 - успешно
function uefiextract_get_platform() {
    if is_linux; then
        if [[ "${OS_MACHINE_NAME}" == "x86_64" ]]; then
            echo "x64_linux"
            return 0
        fi
    elif is_msys; then
        if [[ "${OS_MACHINE_NAME}" == "x86_64" ]]; then
            echo "win64"
            return 0
        elif [[ "${OS_MACHINE_NAME}" == "i386" || "${OS_MACHINE_NAME}" == "i686" ]]; then
            echo "win32"
            return 0
        fi
    fi
    echo "[uefiextract] UNSUPPORTED PLATFORM/ARCH"
    return 1
}

## @brief Получить путь до исполняемого файла uefiextract
## @return Путь до исполняемого файла uefiextract
## @retval 0 - успешно
function uefiextract_get_executable_path() {
   echo "${GLOBAL_CONFIG_OPT_DIR_PATH}/uefiextract/uefiextract"
   return 0
}

## @brief Установить uefiextract
## @details Версия A72
## @details Поддерживаемые платформы Linux|x64, Windows/MSYS2|i386, Windows/MSYS2|i686, Windows/MSYS2|x86_64
## @details Установка в директорию ${GLOBAL_CONFIG_OPT_DIR_PATH}
## @retval 0 - успешно
function uefiextract_setup() {
    local UEFIEXTRACT_PLATFORM=""
    UEFIEXTRACT_PLATFORM=$(uefiextract_get_platform) || return $?

    local DOWNLOAD_URL="https://github.com/LongSoft/UEFITool/releases/download/A72/UEFIExtract_NE_A72_${UEFIEXTRACT_PLATFORM}.zip"
    local INSTALL_DIR_PATH=""
    INSTALL_DIR_PATH=$(dirname "$(uefiextract_get_executable_path)") || return $?

    download_zip_and_unpack "${DOWNLOAD_URL}" "${INSTALL_DIR_PATH}" "remake_dirs" || return $?
    return 0
}

## @brief Извлечь IntelGopDriver из UEFI образа
## @param [in] Путь до UEFI образа материнской платы
## @param [in] Путь до конечного файла куда извлечь IntelGopDriver из UEFI
##             Если файл существует, он будет перезаписан
## @retval 0 - успешно
function uefiextract_get_intel_gop_driver() {
    local UEFI_IMAGE_FILE_PATH="${1}"
    local OUT_INTEL_GOP_DRIVER_FILE_PATH="${2}"
    local INTEL_GOP_DRIVER_UUID="380B6B4F-1454-41F2-A6D3-61D1333E8CB4"

    if ! [[ -e "${UEFI_IMAGE_FILE_PATH}" ]]; then
        return 1
    fi

    local TMP_DIR_PATH=""
    TMP_DIR_PATH=$(mktemp --directory --dry-run) || return $?

    "$(uefiextract_get_executable_path)" "${UEFI_IMAGE_FILE_PATH}" -i "${INTEL_GOP_DRIVER_UUID}" -o "${TMP_DIR_PATH}" -m body &&
    fs_make_dirs "$(dirname "${OUT_INTEL_GOP_DRIVER_FILE_PATH}")" &&
    cp -f "${TMP_DIR_PATH}/body.bin" "${OUT_INTEL_GOP_DRIVER_FILE_PATH}"
    local COMMAND_CHAIN_RESULT=$?
    rm -rf "${TMP_DIR_PATH}"
    return ${COMMAND_CHAIN_RESULT}
}
