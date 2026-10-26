#!/bin/bash

# @file user.include.sh
# @brief Функции работы с пользователями ОС


# @description Установить пакеты работы с пользователями
# @exitcode 0 успешно
function user_setup() {
    if is_msys; then
        return 0
    fi

    if is_termux; then
        termux_user_packages_setup || return $?
        return 0
    fi

    # Утилиты usermod, useradd см. https://pkgs.org/download/passwd
    # passwd для настройки доступа к ssh серверу по паролю
    package_manager_install_packages "passwd" || return $?
    return 0
}

# @description Получить имя текущего пользователя
# @stdout Имя текущего пользователя
# @exitcode 0 успешно
function user_get_current() {
    local USER_NAME=""
    USER_NAME=$(whoami) || return $?
    if [[ -z "${USER_NAME}" ]]; then
        return 1
    fi

    echo "${USER_NAME}"
    return 0
}

# @description Получить имя текущего зарегистрированного пользователя
# Текущий зарегистрированный пользователь - результат команды logname
# @stdout Имя текущего зарегистрированного пользователя
# @exitcode 0 успешно
function user_get_logname() {
    local USER_NAME=""
    USER_NAME=$(logname) || return $?
    if [[ -z "${USER_NAME}" ]]; then
        return 1
    fi

    echo "${USER_NAME}"
    return 0
}

# @description Создать нового пользователя
# @arg $1 string Имя нового пользователя
# @exitcode 0 успешно
function user_create() {
    local USER_NAME="${1}"

    useradd "${USER_NAME}" > "/dev/null" || return $?
    return 0
}

# @description Проверить существует ли пользователь
# @arg $1 string Имя пользователя
# @exitcode 0 пользователь существует
# @exitcode 1 нет
function user_is_exists() {
    local USER_NAME="${1}"

    id "${USER_NAME}" &> "/dev/null" || return $?
    return 0
}

# @description Добавить пользователя в группу
# @arg $1 string Имя пользователя
# @arg $2 string Имя группы
# @exitcode 0 успешно
function user_add_to_group() {
    local USER_NAME="${1}"
    local GROUP_NAME="${2}"

    usermod -a -G "${GROUP_NAME}" "${USER_NAME}" > "/dev/null" || return $?
    return 0
}

# @description Проверить добавлен ли пользователь в группу
# @arg $1 string Имя пользователя
# @arg $2 string Имя группы
# @exitcode 0 пользователь добавлен в группу
# @exitcode 1 нет
function user_is_added_to_group() {
    local USER_NAME="${1}"
    local GROUP_NAME="${2}"

    local USER_GROUP_NAME_LIST=""
    USER_GROUP_NAME_LIST=$(id "${USER_NAME}" -G -n 2> "/dev/null") || return $? # https://www.geeksforgeeks.org/how-to-check-the-groups-a-user-belongs-to-in-linux/
    for USER_GROUP_NAME in USER_GROUP_NAME_LIST; do
        if [[ "${USER_GROUP_NAME,,}" == "${GROUP_NAME,,}" ]]; then
            return 0
        fi
    done
    return 1
}

# @description Проверить пользователя
# Проверяется существование заданного пользователя
# @arg $1 string Имя пользователя, необязательный аргумент (если не задано, будет подставлено имя текущего пользователя)
# @stdout Имя пользователя
# @exitcode 0 успешно
function user_check() {
   local USER_NAME="${1}"

    if [[ -z "${USER_NAME}" ]]; then
        USER_NAME=$(user_get_current) || return $?
    fi

    if ! user_is_exists "${USER_NAME}"; then
        return 1
    fi

    echo "${USER_NAME}"
    return 0
}

# @description Получить домашнюю директорию пользователя
# https://unix.stackexchange.com/a/758316
# В Android/termux возможен только один пользователь, поэтому имя пользователя игнорируется
#         https://wiki.termux.com/wiki/Differences_from_Linux
# @arg $1 string Имя пользователя, необязательный аргумент (если не задано, будет подставлено имя текущего пользователя)
# @stdout Домашняя директория пользователя
# @exitcode 0 успешно
function user_get_home_dir_path() {
    if is_termux; then
        termux_user_get_home_dir_path || return $?
        return 0
    fi

    local USER_NAME="${1}"
    USER_NAME=$(user_check "${USER_NAME}") || return $?

    eval echo "~${USER_NAME}"
    return 0
}

# @description Получить домашнюю директорию текущего зарегистрированного пользователя
# Текущий зарегистрированный пользователь - результат команды logname
# @stdout Домашняя директория текущего зарегистрированного пользователя
# @exitcode 0 успешно, 1 - logname вернул пустое имя пользователя или ошибку
function user_get_logname_home_dir_path() {
    local USER_NAME=""
    USER_NAME=$(user_get_logname) || return $?

    user_get_home_dir_path "${USER_NAME}" || return $?
    return 0
}

# @description Проверить задан ли пароль у пользователя
# @arg $1 string Имя пользователя, необязательный аргумент (если не задано, будет подставлено имя текущего пользователя)
# @exitcode 0 пароль задан
# @exitcode 1 нет
function user_is_exists_password() {
    if is_termux; then
        termux_user_is_exists_password || return $?
        return 0
    fi

    local USER_NAME="${1}"
    USER_NAME=$(user_check "${USER_NAME}" 2> "/dev/null") || return $?

    passwd --status "${USER_NAME}" &> "/dev/null" || return $?
    return 0
}

# @description Создать пользователю пароль если пароль не задан
# @stdout [in] Имя пользователя
# @exitcode 0 успешно
function user_create_password_if() {
    local USER_NAME="${1}"

    USER_NAME=$(user_check "${USER_NAME}") || return $?

    if ! user_is_exists_password "${USER_NAME}"; then
        echo "Set password for \"${USER_NAME}\""
        passwd "${USER_NAME}" || return $?
        return 0
    fi

    return 0
}