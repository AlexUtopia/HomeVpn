#!/bin/bash

## @brief Функции работы с загрузкой/распаковкой файлов


## @brief Установить пакеты загрузки/распаковки файлов
## @retval 0 - успешно
function download_setup() {
    package_manager_install_packages "${GLOBAL_CONFIG_MSYS2_PACKAGE_PREFIX}curl tar ${GLOBAL_CONFIG_MSYS2_PACKAGE_PREFIX}7zip" || return $?
    return 0
}

## @brief Скачать файл
## @details Директория для скачиваемого файла будет создана, если требуется
## @param [in] URL для скачивания
## @param [in] Путь до скачанного файла; можно передать "-" - записать результат в stdout
## @param [in] Скачать файл только если он не скачан (передать download_if_not_exist), необязательный аргумент
##             Если аргумент не задан, файл будет перескачен
## @retval 0 - успешно
function download_file() {
    local URL="${1}"
    local FILE_PATH="${2}"
    local DOWNLOAD_IF_NOT_EXIST="${3}"

    if [[ "${DOWNLOAD_IF_NOT_EXIST}" == "download_if_not_exist" && -e "${FILE_PATH}" ]]; then
        return 0
    fi

    if [[ "${FILE_PATH}" == "-" ]]; then
        curl -L "${URL}" || return $?
    else
        local FILE_DIRECTORY_PATH=""
        FILE_DIRECTORY_PATH=$(dirname "${FILE_PATH}") || return $?
        fs_make_dirs "${FILE_DIRECTORY_PATH}" || return $?
        curl -L --output "${FILE_PATH}" "${URL}" || return $?
    fi
    return 0
}

## @brief Скачать и распаковать tar.gz файл
## @details Директория для распаковки будет создана/пересоздана, если требуется
## @param [in] URL для скачивания
## @param [in] Путь до директории распаковки архива
## @param [in] Не пустая строка (рекомендуется "remake_dirs") - пересоздать директорию распаковки архива, необязательный аргумент
## @param [in] (UInt8) Пропустить часть пути архива при распаковке, необязательный аргумент
## @retval 0 - успешно
function download_targz_and_unpack() {
    local URL="${1}"
    local OUT_DIR_PATH="${2}"
    local IS_REMAKE_OUT_DIR_PATH="${3}"
    local STRIP_COMPONENTS="${4}"

    if [[ -n "${IS_REMAKE_OUT_DIR_PATH}" ]]; then
        fs_remake_dirs "${OUT_DIR_PATH}" || return $?
    else
        fs_make_dirs "${OUT_DIR_PATH}" || return $?
    fi

    if [[ -n "${STRIP_COMPONENTS}" ]]; then
        STRIP_COMPONENTS="--strip-components=${STRIP_COMPONENTS}"
    fi

    download_file "${URL}" "-" | tar -xz -C "${OUT_DIR_PATH}" "${STRIP_COMPONENTS}" || return $?
    return 0
}

## @brief Скачать и распаковать zip файл
## @details Директория для распаковки будет создана/пересоздана, если требуется
## @param [in] URL для скачивания
## @param [in] Путь до директории распаковки архива
## @param [in] Не пустая строка (рекомендуется "remake_dirs") - пересоздать директорию распаковки архива, необязательный аргумент
## @param [in] (UInt8) Пропустить часть пути архива при распаковке, необязательный аргумент
## @retval 0 - успешно
function download_zip_and_unpack() {
    local URL="${1}"
    local OUT_DIR_PATH="${2}"
    local IS_REMAKE_OUT_DIR_PATH="${3}"
    local STRIP_COMPONENTS="${4}" # fixme utopia Пока не поддерживается https://superuser.com/a/573624/2121020

    if [[ -n "${IS_REMAKE_OUT_DIR_PATH}" ]]; then
        fs_remake_dirs "${OUT_DIR_PATH}" || return $?
    else
        fs_make_dirs "${OUT_DIR_PATH}" || return $?
    fi

    local TMP_FILE_PATH=""
    TMP_FILE_PATH=$(mktemp) || return $?

    download_file "${URL}" "${TMP_FILE_PATH}" &&
    7z x "${TMP_FILE_PATH}" -o"${OUT_DIR_PATH}"
    local COMMAND_CHAIN_RESULT=$?
    rm -f "${TMP_FILE_PATH}"
    return ${COMMAND_CHAIN_RESULT}
}