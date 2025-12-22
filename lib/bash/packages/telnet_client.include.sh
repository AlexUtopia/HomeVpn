#!/bin/bash

## @brief Функции работы с telnet клиентом
## https://putty.org.ru/
## @details Требуется для подключения к qemu-monitor
##          https://unix.stackexchange.com/questions/426652/connect-to-running-qemu-instance-with-qemu-monitor
##          https://qemu-project.gitlab.io/qemu/system/monitor.html
##          Получить дерево устройств: info qtree


## @brief Установить telnet клиент
## @retval 0 - успешно
function telnet_client_setup() {
    TELNET_CLIENT_PACKAGE="putty"
    if is_msys; then
        TELNET_CLIENT_PACKAGE="${GLOBAL_CONFIG_MSYS2_PACKAGE_PREFIX}putty"
    fi

    package_manager_install_packages "${TELNET_CLIENT_PACKAGE}" || return $?
    return 0
}