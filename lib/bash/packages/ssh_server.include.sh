#!/bin/bash

## @brief Функции работы с SSH клиентом/сервером
## https://www.openssh.org/
## https://wiki.archlinux.org/title/OpenSSH_(%D0%A0%D1%83%D1%81%D1%81%D0%BA%D0%B8%D0%B9)

# fixme utopia Добавим поддержку "X11Forwarding yes" в "${GLOBAL_CONFIG_ETC_DIR_PATH}/ssh/sshd_config" (termux)
# https://www.reddit.com/r/termux/comments/bd5kz4/x_windows_remote_display/


## @brief Установить пакеты SSH клиента и сервера
## @retval 0 - успешно
function ssh_packages_setup() {
    SSH_CLIENT_PACKAGE="openssh-client"
    if is_termux; then
        SSH_CLIENT_PACKAGE="openssh"
    elif is_msys; then
        SSH_CLIENT_PACKAGE="openssh"
    fi

    SSH_SERVER_PACKAGE="openssh-server"
    if is_termux; then
        SSH_SERVER_PACKAGE="openssh"
    elif is_msys; then
        SSH_SERVER_PACKAGE="openssh"
    fi

    package_manager_install_packages "${SSH_CLIENT_PACKAGE} ${SSH_SERVER_PACKAGE}" || return $?
}

## @brief Установить и настроить SSH сервер
## @retval 0 - успешно
function ssh_server_setup() {
    if [[ -n "${SSH_CONNECTION}" ]]; then
        echo "SSH server is not installed because execution takes place in a SSH session"
        return 0
    fi

    ssh_packages_setup || return $?

    local SSH_SERVER="ssh" # https://tokmakov.msk.ru/blog/item/441

    if is_termux; then
        SSH_SERVER="sshd"
    fi

    service_disable "${SSH_SERVER}"

    user_create_password_if || return $?

    service_enable "${SSH_SERVER}" || return $?

    if ! service_is_active "${SSH_SERVER}"; then
        echo "FATAL: ${SSH_SERVER} not started"
        return 1
    fi
    return 0
}