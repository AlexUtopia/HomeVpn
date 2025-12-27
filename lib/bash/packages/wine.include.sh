#!/bin/bash

## @brief Функции по установке WineHQ
## @details Эмулятор Windows для unix подобных ОС
## https://www.winehq.org/


## @brief Установить последний winetricks
## @details https://github.com/Winetricks/winetricks
## @retval 0 - успешно
function winetricks_setup_latest() {
    local PACKAGE_NAME="winetricks"
    local DOWNLOAD_URL="https://github.com/Winetricks/winetricks/archive/refs/tags/20250102.tar.gz"
    local INSTALL_DIR_PATH="${GLOBAL_CONFIG_OPT_DIR_PATH}/${PACKAGE_NAME}"

    local STRIP_COMPONENTS=1
    download_targz_and_unpack "${DOWNLOAD_URL}" "${INSTALL_DIR_PATH}" "remake_dirs" "${STRIP_COMPONENTS}" || return $?

    make -C "${INSTALL_DIR_PATH}" DESTDIR="${GLOBAL_CONFIG_ROOT_PATH}" install || return $?
    return 0
}

## @brief Установить умолчательный WineHQ
## @details Умолчательный - тот который предоставляется системным менеджером пакетов
## @retval 0 - успешно
function wine_setup_default() {
    local PACKAGE_LIST="wine"
    if is_termux; then
        PACKAGE_LIST="wine-stable"
    fi

    package_manager_install_packages "${PACKAGE_LIST}" || return $?
    return 0
}

## @brief Установить "nightly" сборку WineHQ
## @details https://wiki.winehq.org/Ubuntu
## @retval 0 - успешно
function wine_setup_nightly() {
    if package_manager_is_apt; then
        local OS_DISTRO_VERSION_CODENAME=""
        OS_DISTRO_VERSION_CODENAME=$(get_linux_distro_codename_or_version) || return $?

        local OS_DISTRO_NAME=""
        OS_DISTRO_NAME=$(get_linux_distro_name) || return $?

        local APT_MAIN_ARCH=""
        APT_MAIN_ARCH=$(dpkg_get_main_architecture) || return $?

        local PACKAGE_NAME="winehq-stable"
        local KEY_FILE_URL="https://dl.winehq.org/wine-builds/winehq.key"
        local URIS="https://dl.winehq.org/wine-builds/${OS_DISTRO_NAME}"
        local SUITES="${OS_DISTRO_VERSION_CODENAME}"
        local COMPONENTS="main"
        local ARCHITECTURES="${APT_MAIN_ARCH} i386"
        apt_add_sources "${PACKAGE_NAME}" "${KEY_FILE_URL}" "${URIS}" "${SUITES}" "${COMPONENTS}" "${ARCHITECTURES}" || return $?
        package_manager_install_packages "--install-recommends ${PACKAGE_NAME}" || return $?
        echo "PACKAGE INSTALLED: \"${PACKAGE_NAME}\""
        return 0
    fi
    return 1
}

## @brief Установить 32-ух битные пакеты для запуска 32-ух битных приложений под WineHQ
## @details https://wiki.archlinux.org/title/Wine#32-bit_Windows_applications
## @details https://gitlab.winehq.org/wine/wine/-/wikis/Debian-Ubuntu
## @retval 0 - успешно
function wine_setup_32bit_dependencies() {
    # Зависимости для wine32 fixme utopia Это Ubuntu специфичные пакеты?
    # https://pkgs.org/search/?q=libgl1
    # https://pkgs.org/search/?q=mesa-vulkan-drivers
    package_manager_install_packages "libgl1:i386 mesa-vulkan-drivers:i386" || return $?
    return 0
}

## @brief Установить WineHQ
## @retval 0 - успешно
function wine_setup() {
    if is_msys; then
        return 0
    fi

    if is_termux; then
        # fixme utopia Будем устанавливать в termux для архитектуры amd64/i386? Проверить в termux
        # fixme utopia Запуск из под box86/box64
        # fixme utopia Запуск ARM программ под ARM/wine?
        # https://github.com/termux/termux-packages/blob/master/x11-packages/wine-stable/build.sh
        wine_setup_default || return $?
    else
        wine_setup_32bit_dependencies || return $?
        wine_setup_nightly || wine_setup_default || return $?
    fi

    winetricks_setup_latest || return $?

    # fixme utopia Install Mono and Gecko automatically
    # откуда версию Mono то взять? Курить внимательно appwiz.cpl
    # https://source.winehq.org/winemono.php?arch=x86_64&v=8.1.0&winev=8.19
    # https://gitlab.winehq.org/wine/wine/-/blob/master/dlls/appwiz.cpl/addons.c
    # https://www.winehq.org/pipermail/wine-bugs/2014-January/373915.html

    # https://gist.github.com/RobinCPC/9f42be23a1343600507aabdfecc5061d
    # https://wiki.winehq.org/Mono
    # https://wiki.winehq.org/Gecko
    # https://forum.winehq.org/viewtopic.php?t=37344
    # https://source.winehq.org/

    return 0
}