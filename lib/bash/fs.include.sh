#!/bin/bash

## @brief Функции работы с файловой системой

## @brief Создать директорию
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
