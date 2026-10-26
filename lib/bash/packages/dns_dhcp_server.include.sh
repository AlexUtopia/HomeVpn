#!/bin/bash

# @file dns_dhcp_server.include.sh
# @brief Функции работы с DNS/DHCP сервером dnsmasq
# @description
# https://thekelleys.org.uk/dnsmasq/doc.html
# https://wiki.archlinux.org/title/Dnsmasq
# Требуется для настройки сетевых интерфейсов TAP и сетевого моста виртуальных машин


# @description Установить dnsmasq
# @exitcode 0 успешно
function dns_dhcp_server_setup() {
    if ! is_linux; then
        return 0
    fi

    package_manager_install_packages "dnsmasq-base" || return $?
    return 0
}