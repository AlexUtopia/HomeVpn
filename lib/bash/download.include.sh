#!/bin/bash

# @file download.include.sh
# @brief Функции работы с загрузкой/распаковкой файлов


# @description Установить пакеты загрузки/распаковки файлов (curl, tar, 7zip, ca-certificates)
# @exitcode 0 успешно
function download_setup() {
    package_manager_install_packages "${GLOBAL_CONFIG_MSYS2_PACKAGE_PREFIX}curl tar ${GLOBAL_CONFIG_MSYS2_PACKAGE_PREFIX}7zip ca-certificates" || return $?
    return 0
}

# @description Скачать файл
# Директория для скачиваемого файла будет создана, если требуется
# @arg $1 string URL для скачивания
# @arg $2 string Путь до скачанного файла; можно передать "-" - записать результат в stdout
# @arg $3 string Скачать файл только если он не скачан (передать download_if_not_exist), необязательный аргумент Если аргумент не задан, файл будет перескачан
# @exitcode 0 успешно
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

# @description Скачать и распаковать tar.gz файл
# Директория для распаковки будет создана/пересоздана, если требуется
# @arg $1 string URL для скачивания
# @arg $2 string Путь до директории распаковки архива
# @arg $3 string Не пустая строка (рекомендуется "remake_dirs") - пересоздать директорию распаковки архива, необязательный аргумент
# @arg $4 string (UInt8) Пропустить часть пути архива при распаковке, необязательный аргумент
# @exitcode 0 успешно
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

# @description Скачать и распаковать zip файл
# Директория для распаковки будет создана/пересоздана, если требуется
# Для того чтобы применять wildcards для скрытых файлов используем опцию dotglob
#         https://www.gnu.org/software/bash/manual/bash.html#The-Shopt-Builtin-1
# @arg $1 string URL для скачивания
# @arg $2 string Путь до директории распаковки архива
# @arg $3 string Не пустая строка (рекомендуется "remake_dirs") - пересоздать директорию распаковки архива, необязательный аргумент
# @arg $4 string (UInt8) Пропустить часть пути архива при распаковке, необязательный аргумент
# @exitcode 0 успешно
function download_zip_and_unpack() {
    local URL="${1}"
    local OUT_DIR_PATH="${2}"
    local IS_REMAKE_OUT_DIR_PATH="${3}"
    local STRIP_COMPONENTS="${4}"

    if [[ -n "${IS_REMAKE_OUT_DIR_PATH}" ]]; then
        fs_remake_dirs "${OUT_DIR_PATH}" || return $?
    else
        fs_make_dirs "${OUT_DIR_PATH}" || return $?
    fi

    STRIP_COMPONENTS=$(str_repeat "/*" "${STRIP_COMPONENTS}")

    local TEMP_FILE_PATH=""
    local TEMP_DIR_PATH=""
    TEMP_FILE_PATH=$(mktemp) && trap_add_remove_temp_path_handler "${TEMP_FILE_PATH}" &&
    download_file "${URL}" "${TEMP_FILE_PATH}" &&
    TEMP_DIR_PATH=$(mktemp --directory) && trap_add_remove_temp_path_handler "${TEMP_DIR_PATH}" &&
    7z x "${TEMP_FILE_PATH}" -o"${TEMP_DIR_PATH}" &&
    chmod -R a+rX "${TEMP_DIR_PATH}" &&
    (shopt -s dotglob && mv "${TEMP_DIR_PATH}"/*${STRIP_COMPONENTS} "${OUT_DIR_PATH}/") || return $?
    return 0
}