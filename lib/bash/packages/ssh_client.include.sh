#!/bin/bash

## @brief Функции работы с SSH клиентом
## https://www.openssh.org/
## https://wiki.archlinux.org/title/OpenSSH_(%D0%A0%D1%83%D1%81%D1%81%D0%BA%D0%B8%D0%B9)


# @brief 255 - специальный код ошибки обозначающий что соединение с ssh сервером установить не удалось
# @details Все прочие коды ошибок - результат выполнения удалённой команды
SSH_CLIENT_CONNECTION_ERROR_CODE=255


## @brief Установить SSH клиент
## @retval 0 - успешно
function ssh_client_setup() {
    local PACKAGE_LIST="openssh-client"
    if is_termux; then
        PACKAGE_LIST="openssh"
    elif is_msys; then
        PACKAGE_LIST="openssh"
    fi

    package_manager_install_packages "${PACKAGE_LIST}" || return $?
    return 0
}

## @brief Получить путь до приватного ssh ключа для пользователя
## @details Если текущий хост не имеет ssh ключа (публичный/приватный),
##          ключ будет сгенерирован автоматически (без запросов пользователю)
## @param [in] Имя пользователя, необязательный аргумент (если не задано, будет подставлено имя текущего пользователя)
## @return Путь до приватного ssh ключа для пользователя
## @retval 0 - успешно
function ssh_client_get_private_key_file_path() {
    local USER_NAME="${1}"

    local USER_HOME_DIR_PATH=""
    USER_HOME_DIR_PATH=$(user_get_home_dir_path "${USER_NAME}") || return $?
    local SSH_PRIVATE_KEY_FILE_PATH="${USER_HOME_DIR_PATH}/.ssh/id_rsa"
    if ! [[ -e "${SSH_PRIVATE_KEY_FILE_PATH}" ]]; then
        ssh-keygen -q -N "" -f "${SSH_PRIVATE_KEY_FILE_PATH}" || return $?
    fi
    echo "${SSH_PRIVATE_KEY_FILE_PATH}"
    return 0
}

## @brief Получить путь до приватного ssh ключа для текущего зарегистрированного пользователя
## @details Текущий зарегистрированный пользователь - результат команды logname
## @return Путь до приватного ssh ключа для текущего зарегистрированного пользователя
## @retval 0 - успешно, 1 - logname вернул пустое имя пользователя или ошибку
function ssh_client_get_private_key_file_path_for_logname_user() {
    local USER_NAME=""
    USER_NAME=$(user_get_logname) || return $?

    ssh_client_get_private_key_file_path "${USER_NAME}" || return $?
    return 0
}
