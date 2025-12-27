#!/bin/bash

## @brief Функции работы с VNC сервером


## @brief Установить пакеты для VNC сервера
## @details Пакет autocutsel используется для организации буфера обмена для VNC сессии,
##          см. https://superuser.com/a/1524282
## @details Пакет x11-xserver-utils / xorg-xhost содержит утилиту xhost
##          с помощью которой можно получить root права на запуск графических приложений
## @retval 0 - успешно
function vnc_server_packages_setup() {
    if is_msys; then
        # https://sourceforge.net/projects/tigervnc/files/stable/1.15.0/
        # Под Windows tigervnc server больше не поддерживается, но он есть,
        # см. https://github.com/TigerVNC/tigervnc?tab=readme-ov-file#windows-specific
        return 0
    fi

    # fixme utopia pcregrep и findutils здесь временно
    local PACKAGE_LIST="pcregrep findutils tigervnc-standalone-server tigervnc-xorg-extension x11-xserver-utils autocutsel"
    if is_termux; then
        PACKAGE_LIST="tigervnc xorg-xhost"
    fi

    package_manager_install_packages "${PACKAGE_LIST}" || return $?
    return 0
}