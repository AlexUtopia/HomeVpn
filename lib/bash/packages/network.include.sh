#!/bin/bash

# @file network.include.sh
# @brief Функции для работы с сетью
# @description
# https://wiki.linuxfoundation.org/networking/iproute2
# https://wiki.archlinux.org/title/Dnsmasq
# Требуется для настройки сетевых интерфейсов TAP и сетевого моста виртуальных машин


# @description Установить iproute2
# @exitcode 0 успешно
function network_setup() {
    if is_msys; then
        return 0
    fi

    package_manager_install_packages "iproute2" || return $?
    return 0
}