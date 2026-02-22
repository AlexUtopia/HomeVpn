#!/bin/bash

## @brief Функции работы с SSH сервером
## https://www.openssh.org/
## https://wiki.archlinux.org/title/OpenSSH_(%D0%A0%D1%83%D1%81%D1%81%D0%BA%D0%B8%D0%B9)

# fixme utopia Добавим поддержку "X11Forwarding yes" в "${GLOBAL_CONFIG_ETC_DIR_PATH}/ssh/sshd_config" (termux)
# https://www.reddit.com/r/termux/comments/bd5kz4/x_windows_remote_display/


## @brief Установить пакет SSH сервера
## @retval 0 - успешно
function ssh_packages_setup() {
    local PACKAGE_LIST="openssh-server"
    if is_termux; then
        PACKAGE_LIST="openssh"
    elif is_msys; then
        PACKAGE_LIST="openssh"
    fi

    package_manager_install_packages "${PACKAGE_LIST}" || return $?
    return 0
}

## @brief Установить и настроить SSH сервер
## @retval 0 - успешно
function ssh_server_setup() {
    local SSH_SERVER="ssh" # https://tokmakov.msk.ru/blog/item/441
    if is_termux; then
        SSH_SERVER="sshd"
    fi

    if [[ -n "${SSH_CONNECTION}" ]]; then
        echo "SSH server is not installed because execution takes place in a SSH session"

        # Включаем службу если скрипт исполняется внутри SSH сессии (это контринтуитивно)
        # Это требуется в специфическом сценарии работы с Waydroid/termux:
        # 1) sshd запускаем вручную при помощи отправки клавиатурных событий в termux
        # 1.1) настройку runit (termux-services) таким способом не делаем, т.к. у нас нет обратной связи (т.е. stdout termux)
        # 2) подключаемся к termux по ssh
        # 3) исполняем данный скрипт
        # 4) добавляем sshd в автозапуск, реального запуска sshd не произойдёт, т.к. он уже запущен
        service_enable "${SSH_SERVER}"
        return 0
    fi

    ssh_packages_setup || return $?

    service_disable "${SSH_SERVER}"

    user_create_password_if || return $?

    service_enable "${SSH_SERVER}" || return $?

    if ! service_is_active "${SSH_SERVER}"; then
        echo "FATAL: ${SSH_SERVER} not started"
        return 1
    fi
    return 0
}