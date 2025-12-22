#!/bin/bash

## @brief Функции работы с DNS/DHCP сервером dnsmasq
## https://thekelleys.org.uk/dnsmasq/doc.html
## https://wiki.archlinux.org/title/Dnsmasq
## @details Требуется для настройки сетевых интерфейсов TAP и сетевого моста виртуальных машин


## @brief Установить dnsmasq
## @retval 0 - успешно
function dnsmasq_setup() {
    if is_termux || is_msys; then
        return 0
    fi

    package_manager_install_packages "dnsmasq-base" || return $?
    return 0
}