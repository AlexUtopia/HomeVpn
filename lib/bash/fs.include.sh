#!/bin/bash

## @brief Функции работы с файловой системой


## @brief Создать директорию (директории)
## @details Не генерировать ошибку если директория существует
## @param [in] Путь до целевой директории
## @param [in] Пользователь от которого создавать директорию, необязательный аргумент
## @retval 0 - успешно
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

## @brief Пересоздать директорию
## @param [in] Путь до целевой директории
## @param [in] Пользователь от которого создавать директорию, необязательный аргумент
## @retval 0 - успешно
function fs_remake_dirs() {
    local DIR_PATH="${1}"
    local USER_NAME="${2}"

    rm -rf "${DIR_PATH}" > "/dev/null" || return $?
    fs_make_dirs "${DIR_PATH}" "${USER_NAME}" > "/dev/null" || return $?
    return 0
}

## @brief Создать символическую ссылку
## @param [in] Исходный путь (оригинальный файл или директория)
## @param [in] Целевой путь
## @retval 0 - успешно
function fs_create_symlink() {
    local SOURCE_PATH="${1}"
    local TARGET_PATH="${2}"

    # В termux почему-то опция -f у ln не всегда срабатывает, поэтому удалим символическую ссылку вручную
    rm -rf "${TARGET_PATH}" > "/dev/null" || return $?
    ln -s "${SOURCE_PATH}" "${TARGET_PATH}" > "/dev/null" || return $?
    return 0
}

## @brief Сделать файл исполняемым
## @param [in] Путь до файла
## @retval 0 - успешно
function fs_set_file_as_executable() {
    local FILE_PATH="${1}"

    chmod +x "${FILE_PATH}" > "/dev/null" || return $?
    return 0
}

## @brief "Деактивировать" существующий файл
## @details Под "деактивацией" подразумевается переименование целевого файла в
##          <название_файла>_unused_since_<дата/время с точностью до нс в UTC>
## @param [in] Путь до файла
## @retval 0 - успешно
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

## @brief Подготовиться к созданию файла
## @details Подготовка состоит:
##          1) создать директорию (директории)
##          2) "деактивировать" файл если требуется
## @param [in] Путь до файла
## @param [in] Пользователь от которого создавать директорию, необязательный аргумент
## @param [in] Если "деактивировать" файл не требуется, то передать "rewrite_if_exist", необязательный аргумент
## @retval 0 - успешно
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

## @brief Создать файл
## @param [in] Содержимое файла
## @param [in] Путь до файла
## @param [in] Пользователь от которого создавать директорию, необязательный аргумент
## @param [in] Если "деактивировать" файл не требуется, то передать "rewrite_if_exist", необязательный аргумент
## @retval 0 - успешно
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

## @brief Подождать создания директории
## @param [in] Путь до отслеживаемой директории
## @param [in] Время ожидания в секундах, необязательный аргумент (если не задано, = 10 секунд)
## @retval 0 - успешно
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
