#!/bin/bash

## @brief Функции работы с SSH клиентом
## https://www.openssh.org/
## https://wiki.archlinux.org/title/OpenSSH_(%D0%A0%D1%83%D1%81%D1%81%D0%BA%D0%B8%D0%B9)


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