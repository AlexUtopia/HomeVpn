#!/bin/bash

## @brief Функции работы с пользователями ОС


## @brief Установить пакеты работы с пользователями
## @retval 0 - успешно
function user_packages_setup() {
    PASSWD_PACKAGE="passwd" # Утилиты usermod, useradd см. https://pkgs.org/download/passwd
                            # passwd для настройки доступа к ssh серверу по паролю
    if is_termux; then
        termux_user_packages_setup || return $?
        return 0
    elif is_msys; then
        PASSWD_PACKAGE=""
    fi
    package_manager_install_packages "${PASSWD_PACKAGE}" || return $?
    return 0
}

## @brief Получить имя текущего пользователя
## @return [in] Имя текущего пользователя
## @retval 0 - успешно
function user_get_current() {
   local RESULT=""
   RESULT=$(whoami) || return $?
   echo "${RESULT}"
   return 0
}

## @brief Создать нового пользователя
## @param [in] Имя нового пользователя
## @retval 0 - успешно
function user_create() {
    local USER_NAME="${1}"

    useradd "${USER_NAME}" > "/dev/null" || return $?
    return 0
}

## @brief Проверить существует ли пользователь
## @param [in] Имя пользователя
## @retval 0 - пользователь существует; 1 - нет
function user_is_exists() {
    local USER_NAME="${1}"

    id "${USER_NAME}" &> "/dev/null" || return $?
    return 0
}

## @brief Добавить пользователя в группу
## @param [in] Имя пользователя
## @param [in] Имя группы
## @retval 0 - успешно
function user_add_to_group() {
    local USER_NAME="${1}"
    local GROUP_NAME="${2}"

    usermod -a -G "${GROUP_NAME}" "${USER_NAME}" > "/dev/null" || return $?
    return 0
}

## @brief Проверить добавлен ли пользователь в группу
## @param [in] Имя пользователя
## @param [in] Имя группы
## @retval 0 - пользователь добавлен в группу; 1 - нет
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

## @brief Проверить пользователя
## @details Проверяется существование заданного пользователя
## @param [in] Имя пользователя, необязательный аргумент (если не задано, будет подставлено имя текущего пользователя)
## @return Имя пользователя
## @retval 0 - успешно
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

## @brief Получить домашнюю директорию пользователя
## @details https://unix.stackexchange.com/a/758316
## @details В Android/termux возможен только один пользователь, поэтому имя пользователя игнорируется
##          https://wiki.termux.com/wiki/Differences_from_Linux
## @param [in] Имя пользователя, необязательный аргумент (если не задано, будет подставлено имя текущего пользователя)
## @retval 0 - успешно
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

## @brief Проверить задан ли пароль у пользователя
## @param [in] Имя пользователя, необязательный аргумент (если не задано, будет подставлено имя текущего пользователя)
## @retval 0 - пароль задан; 1 - нет
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

## @brief Создать пользователю пароль если пароль не задан
## @return [in] Имя пользователя
## @retval 0 - успешно
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