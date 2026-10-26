#!/bin/bash

# @file apt.include.sh
# @brief Функции работы с пакетным менеджером apt


# @description Получить главную архитектуру пакетов
# @stdout Главная архитектура пакетов, например, amd64 или aarch64
# @exitcode 0 успешно
function dpkg_get_main_architecture() {
    local RESULT=""
    RESULT=$(dpkg --print-architecture) || return $?
    echo "${RESULT}"
    return 0
}

# @description Установить список пакетов
# Список может состоять из одного пакета
# @arg $1 string Список пакетов
# @exitcode 0 успешно
function apt_install_packages() {
    local PACKAGE_NAME_LIST="${1}"

    apt -y install ${PACKAGE_NAME_LIST} || return $?
    return 0
}

# @description Обновить установленные пакеты
# @exitcode 0 успешно
function apt_update_and_upgrade() {
    # https://wiki.debian.org/Multiarch/HOWTO
    # https://wiki.ubuntu.com/MultiarchCross
    dpkg --add-architecture "i386" || return $? # Для установки wine требуется добавить i386 архитектуру
                                              # https://wiki.archlinux.org/title/Wine#32-bit_Windows_applications
                                              # https://gitlab.winehq.org/wine/wine/-/wikis/Debian-Ubuntu
    apt update || return $?
    apt upgrade -o Dpkg::Options::="--force-confnew" -y || return $?

    if is_termux; then
        termux_apt_repo_packages_setup || return $?
    fi

    apt_install_packages "gnupg" || return $? # Используется для функции apt_download_key()
    return 0
}

# @description Проверить установлен ли пакет
# @arg $1 string Имя пакета
# @exitcode 0 пакет установлен, 1 - нет
function apt_is_package_installed() {
    local PACKAGE_NAME="${1}"

    apt -L "${PACKAGE_NAME}" &> "/dev/null" || return $?
    return 0
}

# @description Проверить существует (доступен) ли пакет в репозитории пакетов
# @arg $1 string Имя пакета
# @exitcode 0 пакет существует (доступен) в репозитории пакетов, 1 - нет
function apt_is_package_exists_in_repository() {
    local PACKAGE_NAME="${1}"

    apt-cache show "${PACKAGE_NAME}" &> "/dev/null" || return $?
    return 0
}

# @description Создать source файл в формате deb822 для apt
# https://wiki.debian.org/ArchitectureSpecificsMemo
# https://manpages.ubuntu.com/manpages/xenial/man5/sources.list.5.html
# @arg $1 string Путь куда сформировать *.source файл
# @arg $2 string URIs параметр (обязательный)
# @arg $3 string Suites параметр (обязательный)
# @arg $4 string Components параметр (обязательный)
# @arg $5 string Signed-By параметр (не обязательный)
# @arg $6 string Architectures параметр (не обязательный, будет использована архитектура по умолчанию)
# @arg $7 string Types параметр (не обязательный, будет "deb")
# @exitcode 0 успешно
function apt_create_sources() {
    local SOURCES_FILE_PATH="${1}"
    local URIS="${2}"
    local SUITES="${3}"
    local COMPONENTS="${4}"

    local SIGNED_BY="${5}"
    local SIGNED_BY_PATH=""
    if [[ -n "${SIGNED_BY}" ]]; then
        SIGNED_BY_PATH="Signed-By: ${SIGNED_BY}"
    fi

    local ARCHITECTURES="${6}"
    if [[ -z "${ARCHITECTURES}" ]]; then
        ARCHITECTURES=$(dpkg_get_main_architecture) || return $?
    fi

    local TYPES="${7}"
    if [[ -z "${TYPES}" ]]; then
        TYPES="deb"
    fi

    fs_create_file "Types: ${TYPES}
URIs: ${URIS}
Suites: ${SUITES}
Components: ${COMPONENTS}
Architectures: ${ARCHITECTURES}
${SIGNED_BY_PATH}" "${SOURCES_FILE_PATH}" || return $?
    return 0
}

# @description Получить путь до файла ключа пакета
# https://habr.com/ru/articles/683716/
# @arg $1 string Имя пакета
# @stdout Путь до файла ключа пакет
# @exitcode 0 успешно
function apt_get_key_file_path() {
    local PACKAGE_NAME="${1}"

    local KEYRINGS_DIR_PATH="${GLOBAL_CONFIG_ETC_DIR_PATH}/apt/keyrings"

    echo "${KEYRINGS_DIR_PATH}/${PACKAGE_NAME}.gpg"
    return 0
}

# @description Получить путь до sources-файла пакета
# https://habr.com/ru/articles/683716/
# @arg $1 string Имя пакета
# @stdout Путь до sources-файла пакета
# @exitcode 0 успешно
function apt_get_source_file_path() {
    local PACKAGE_NAME="${1}"
    local APT_SOURCES_LIST_DIR_PATH="${GLOBAL_CONFIG_ETC_DIR_PATH}/apt/sources.list.d"

    echo "${APT_SOURCES_LIST_DIR_PATH}/${PACKAGE_NAME}.sources"
    return 0
}

# @description Скачать ключ пакета
# @arg $1 string Имя пакета
# @arg $2 string URL для скачивания ключа пакета
# @exitcode 0 успешно
function apt_download_key() {
    local PACKAGE_NAME="${1}"
    local KEY_FILE_URL="${2}"

    if [[ -z "${KEY_FILE_URL}" ]]; then
        echo ""
        return 0
    fi

    local KEY_FILE_PATH=""
    KEY_FILE_PATH=$(apt_get_key_file_path "${PACKAGE_NAME}") || return $?

    if [[ -f "${KEY_FILE_PATH}" ]]; then
        echo "${KEY_FILE_PATH}"
        return 0
    fi

    download_file "${KEY_FILE_URL}" "-" | gpg --dearmor > "${KEY_FILE_PATH}" || return $?
    echo "${KEY_FILE_PATH}"
    return 0
}

# @description Добавить source файл в формате deb822 для apt
# https://wiki.debian.org/ArchitectureSpecificsMemo
# https://manpages.ubuntu.com/manpages/xenial/man5/sources.list.5.html
# @arg $1 string Имя пакета
# @arg $2 string URL для скачивания ключа пакета
# @arg $3 string URIs параметр (обязательный)
# @arg $4 string Suites параметр (обязательный)
# @arg $5 string Components параметр (обязательный)
# @arg $6 string Architectures параметр (не обязательный, будет использована архитектура по умолчанию)
# @arg $7 string Types параметр (не обязательный, будет "deb")
# @exitcode 0 успешно
function apt_add_sources() {
    local PACKAGE_NAME="${1}"
    local KEY_FILE_URL="${2}"
    local URIS="${3}"
    local SUITES="${4}"
    local COMPONENTS="${5}"
    local ARCHITECTURES="${6}"
    local TYPES="${7}"

    local SOURCE_FILE_PATH=""
    SOURCE_FILE_PATH=$(apt_get_source_file_path "${PACKAGE_NAME}") || return $?
    if [[ -f "${SOURCE_FILE_PATH}" ]]; then
        echo "WARNING: \"${SOURCE_FILE_PATH}\" already exists"
        return 0
    fi

    local KEY_FILE_PATH=""
    KEY_FILE_PATH=$(apt_download_key "${PACKAGE_NAME}" "${KEY_FILE_URL}") || return $?

    apt_create_sources "${SOURCE_FILE_PATH}" "${URIS}" "${SUITES}" "${COMPONENTS}" "${KEY_FILE_PATH}" "${ARCHITECTURES}" "${TYPES}" || return $?

    apt update
    local APT_UPDATE_RESULT=$?
    if ! check_return_code ${APT_UPDATE_RESULT}; then
        rm -f "${SOURCE_FILE_PATH}" "${KEY_FILE_PATH}"
        return ${APT_UPDATE_RESULT}
    fi
    return 0
}

# @description Добавить ppa репозиторий для apt
# @arg $1 string Имя ppa репозитория, например "deadsnakes/ppa"
# @arg $2 string Подпись ppa репозитория, необязательный аргумент
# @exitcode 0 успешно
function apt_add_ppa() {
    local PPA_NAME="${1}"

    # https://askubuntu.com/a/1458126
    # add-apt-repository -y "ppa:deadsnakes/ppa" тоже самое что и
    #
    # local PPA_NAME="deadsnakes/ppa"
    # local FINGERPRINT="${2}" // "F23C5A6CF475977595C89F51BA6932366A755776"
    # local KEY_FILE_URL="https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x${FINGERPRINT}"
    # local URIS="https://ppa.launchpadcontent.net/${PPA_NAME}/ubuntu"
    # local SUITES="${OS_DISTRO_VERSION_CODENAME}"
    # local COMPONENTS="main"
    # apt_add_sources "${PPA_NAME//\//-}-${SUITES}" "${KEY_FILE_URL}" "${URIS}" "${SUITES}" "${COMPONENTS}" || return $?

    add-apt-repository -y "ppa:${PPA_NAME}" || return $?
    apt update || return $?
    return 0
}


function apt_package_manager_install_package_from_file() {
    local PACKAGE_INSTALLER_FILE_PATH="${1}"

    dpkg -i "${PACKAGE_INSTALLER_FILE_PATH}" || return $?
    return 0
}