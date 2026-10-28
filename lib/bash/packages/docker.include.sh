#!/bin/bash

# @file docker.include.sh
# @brief Функции установки Docker
# @description
# Docker Engine для Linux (пакетный менеджер apt)
# https://docs.docker.com/engine/install/ubuntu/
# https://docs.docker.com/engine/install/debian/
#
# **Внимание:** членство в группе docker применяется после повторного входа пользователя


# @description Установить Docker из официального репозитория
# @exitcode 0 успешно
function docker_packages_setup() {
    local OS_DISTRO_VERSION_CODENAME=""
    OS_DISTRO_VERSION_CODENAME=$(get_linux_distro_codename_or_version) || return $?

    local OS_DISTRO_NAME=""
    OS_DISTRO_NAME=$(get_linux_distro_name) || return $?

    local PACKAGE_NAME="docker"
    local URIS="https://download.docker.com/linux/${OS_DISTRO_NAME}"
    local KEY_FILE_URL="${URIS}/gpg"
    local SUITES="${OS_DISTRO_VERSION_CODENAME}"
    local COMPONENTS="stable"
    apt_add_sources "${PACKAGE_NAME}" "${KEY_FILE_URL}" "${URIS}" "${SUITES}" "${COMPONENTS}" || return $?

    local PACKAGE_LIST="docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin"
    package_manager_install_packages "${PACKAGE_LIST}" || return $?
    return 0
}

# @description Добавить службу Docker в автозапуск и запустить
# @exitcode 0 успешно
function docker_service_setup() {
    local DOCKER_SERVICE="docker"

    service_enable "${DOCKER_SERVICE}" || return $?

    if ! service_is_active "${DOCKER_SERVICE}"; then
        echo "FATAL: ${DOCKER_SERVICE} not started"
        return 1
    fi
    return 0
}

# @description Добавить текущего пользователя (logname) в группу docker
# @exitcode 0 успешно
function docker_user_setup() {
    local USER_NAME=""
    USER_NAME=$(user_get_logname) || return $?

    user_add_to_group "${USER_NAME}" "docker" || return $?
    return 0
}

# @description Установить и настроить Docker
# @exitcode 0 успешно
function docker_setup() {
    if ! package_manager_is_apt; then
        return 0
    fi

    docker_packages_setup || return $?
    docker_service_setup || return $?
    docker_user_setup || return $?
    return 0
}
