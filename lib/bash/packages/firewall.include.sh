#!/bin/bash

# @file firewall.include.sh
# @brief Функции работы с файерволом
# @description
# https://www.netfilter.org/projects/iptables/index.html
# https://wiki.archlinux.org/title/Iptables_(%D0%A0%D1%83%D1%81%D1%81%D0%BA%D0%B8%D0%B9)
# Требуется для настройки сетевых интерфейсов TAP и сетевого моста виртуальных машин


# @description Установить файервол
# Утилита sysctl (пакет procps) используется для записи параметров ядра Linux:
#         sysctl -w net.ipv4.ip_forward=1 - разрешить перенаправление IPv4 траффика
# @exitcode 0 успешно
function firewall_setup() {
    local PACKAGE_LIST="iptables procps"
    if is_msys; then
        PACKAGE_LIST="procps-ng" # fixme utopia Для Windows это бесполезный пакет?
    fi

    package_manager_install_packages "${PACKAGE_LIST}" || return $?
    return 0
}