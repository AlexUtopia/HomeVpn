#!/bin/bash

# @file fs.include.sh
# @brief Функции работы с файловой системой


# @description Создать директорию (директории)
# Не генерировать ошибку если директория существует
# @arg $1 string Путь до целевой директории
# @arg $2 string Пользователь от которого создавать директорию, необязательный аргумент
# @exitcode 0 успешно
function fs_make_dirs() {
    local DIR_PATH="${1}"
    local USER_NAME="${2}"

    if [[ -n "${USER_NAME}" ]]; then
        sudo --user="${USER_NAME}" mkdir -p "${DIR_PATH}" > "/dev/null" || return $?
    else
        mkdir -p "${DIR_PATH}" > "/dev/null" || return $?
    fi
    return 0
}

# @description Пересоздать директорию
# @arg $1 string Путь до целевой директории
# @arg $2 string Пользователь от которого создавать директорию, необязательный аргумент
# @exitcode 0 успешно
function fs_remake_dirs() {
    local DIR_PATH="${1}"
    local USER_NAME="${2}"

    rm -rf "${DIR_PATH}" > "/dev/null" || return $?
    fs_make_dirs "${DIR_PATH}" "${USER_NAME}" > "/dev/null" || return $?
    return 0
}

# @description Создать символическую ссылку
# @arg $1 string Исходный путь (оригинальный файл или директория)
# @arg $2 string Целевой путь
# @arg $3 string Пользователь от которого создавать директорию, необязательный аргумент
# @exitcode 0 успешно
function fs_create_symlink() {
    local SOURCE_PATH="${1}"
    local TARGET_PATH="${2}"
    local USER_NAME="${3}"

    if [[ -n "${USER_NAME}" ]]; then
        # В termux почему-то опция -f у ln не всегда срабатывает, поэтому удалим символическую ссылку вручную
        sudo --user="${USER_NAME}" rm -rf "${TARGET_PATH}" > "/dev/null" || return $?
        sudo --user="${USER_NAME}" ln -s "${SOURCE_PATH}" "${TARGET_PATH}" > "/dev/null" || return $?
    else
        rm -rf "${TARGET_PATH}" > "/dev/null" || return $?
        ln -s "${SOURCE_PATH}" "${TARGET_PATH}" > "/dev/null" || return $?
    fi
    return 0
}

# @description Сделать файл исполняемым
# @arg $1 string Путь до файла
# @exitcode 0 успешно
function fs_set_file_as_executable() {
    local FILE_PATH="${1}"

    chmod +x "${FILE_PATH}" > "/dev/null" || return $?
    return 0
}

# @description "Деактивировать" существующий файл
# Под "деактивацией" подразумевается переименование целевого файла в
#         <название_файла>_unused_since_<дата/время с точностью до нс в UTC>
# @arg $1 string Путь до файла
# @exitcode 0 успешно
function fs_deactivate_file_if_exists() {
    local FILE_PATH="${1}"

    if [[ -f "${FILE_PATH}" ]]; then
        local CURRENT_DATE_TIME=""
        CURRENT_DATE_TIME=$(date "+%Y-%m-%dT%H_%M_%S_%N%z") || return $?

        local FILE_NAME=""
        FILE_NAME=$(basename "${FILE_PATH}") || return $?

        local FILE_DIR_PATH=""
        FILE_DIR_PATH=$(dirname "${FILE_PATH}") || return $?

        local DEACTIVATE_FILE_PATH="${FILE_DIR_PATH}/unused_since_${CURRENT_DATE_TIME}_${FILE_NAME}"
        echo "File exist (\"${FILE_PATH}\"), rename to \"${DEACTIVATE_FILE_PATH}\""
        mv "${FILE_PATH}" "${DEACTIVATE_FILE_PATH}" || return $?
    fi
    return 0
}

# @description Подготовиться к созданию файла
# Подготовка состоит:
#         1) создать директорию (директории)
#         2) "деактивировать" файл если требуется
# @arg $1 string Путь до файла
# @arg $2 string Пользователь от которого создавать директорию, необязательный аргумент
# @arg $3 string Если "деактивировать" файл не требуется, то передать "rewrite_if_exist", необязательный аргумент
# @exitcode 0 успешно
function fs_prepare_for_create_file() {
    local FILE_PATH="${1}"
    local USER_NAME="${2}"
    local REWRITE_IF_EXIST="${3}"

    local FILE_DIR_PATH=""
    FILE_DIR_PATH=$(dirname "${FILE_PATH}") || return $?

    fs_make_dirs "${FILE_DIR_PATH}" "${USER_NAME}" || return $?

    if [[ -z "${REWRITE_IF_EXIST}" ]]; then
        fs_deactivate_file_if_exists "${FILE_PATH}" || return $?
    fi
    return 0
}

# @description Создать файл
# @arg $1 string Содержимое файла
# @arg $2 string Путь до файла
# @arg $3 string Пользователь от которого создавать директорию, необязательный аргумент
# @arg $4 string Если "деактивировать" файл не требуется, то передать "rewrite_if_exist", необязательный аргумент
# @exitcode 0 успешно
function fs_create_file() {
    local CONTENT="${1}"
    local FILE_PATH="${2}"
    local USER_NAME="${3}"
    local REWRITE_IF_EXIST="${4}"

    fs_prepare_for_create_file "${FILE_PATH}" "${USER_NAME}" "${REWRITE_IF_EXIST}" || return $?

    if [[ -n "${USER_NAME}" ]]; then
        sudo --user="${USER_NAME}" "${SHELL}" -c "echo '${CONTENT}' > \"${FILE_PATH}\"" || return $?
    else
        "${SHELL}" -c "echo '${CONTENT}' > \"${FILE_PATH}\"" || return $?
    fi
    return 0
}

# @description Подождать создания директории
# @arg $1 string Путь до отслеживаемой директории
# @arg $2 string Время ожидания в секундах, необязательный аргумент (если не задано, = 10 секунд)
# @exitcode 0 успешно
function fs_wait_for_dir_creation() {
    local TARGET_DIR_PATH="${1}"
    local WAIT_SECONDS_COUNT=${2}
    if [[ -z "${WAIT_SECONDS_COUNT}" ]]; then
         WAIT_SECONDS_COUNT=10
    fi

    for (( i = 0; i < WAIT_SECONDS_COUNT; i++ )); do
        if [[ -d "${TARGET_DIR_PATH}" ]]; then
            return 0
        fi
        sleep 1
    done
    return 1
}
