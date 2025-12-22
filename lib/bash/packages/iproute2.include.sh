#!/bin/bash

## @brief Функции работы с iproute2 - набор утилит для работы с сетью
## https://wiki.linuxfoundation.org/networking/iproute2
## https://wiki.archlinux.org/title/Dnsmasq
## @details Требуется для настройки сетевых интерфейсов TAP и сетевого моста виртуальных машин


## @brief Установить dnsmasq
## @retval 0 - успешно
function iproute2_setup() {
    if is_msys; then
        return 0
    fi

    package_manager_install_packages "iproute2" || return $?
    return 0
}