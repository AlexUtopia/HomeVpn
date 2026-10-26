#!/bin/bash

# @file telnet_client.include.sh
# @brief Функции работы с telnet клиентом
# @description
# https://putty.org.ru/
# Требуется для подключения к qemu-monitor
#          https://unix.stackexchange.com/questions/426652/connect-to-running-qemu-instance-with-qemu-monitor
#          https://qemu-project.gitlab.io/qemu/system/monitor.html
#          Получить дерево устройств: info qtree


# @description Установить telnet клиент
# @exitcode 0 успешно
function telnet_client_setup() {
    local PACKAGE_LIST="putty"
    if is_msys; then
        PACKAGE_LIST="${GLOBAL_CONFIG_MSYS2_PACKAGE_PREFIX}putty"
    fi

    package_manager_install_packages "${PACKAGE_LIST}" || return $?
    return 0
}