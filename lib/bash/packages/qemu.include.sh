#!/bin/bash

## @brief Функции работы с qemu
## https://www.qemu.org/
## https://gitlab.com/qemu-project/qemu


## @brief Установить пакеты требуемые для сборки qemu
## @retval 0 - успешно
function qemu_build_setup_dependencies() {
    local REQUIRED_ADDITIONAL_PACKAGES="libglib2.0-dev libfdt-dev libpixman-1-dev zlib1g-dev ninja-build"
    local RECOMMENDED_ADDITIONAL_PACKAGES="libaio-dev libbluetooth-dev libcapstone-dev libbrlapi-dev libbz2-dev libcap-ng-dev libcurl4-gnutls-dev libgtk-3-dev libibverbs-dev libjpeg8-dev libncurses5-dev libnuma-dev librbd-dev librdmacm-dev libsasl2-dev libsdl2-dev libseccomp-dev libsnappy-dev libssh-dev valgrind xfslibs-dev"

    package_manager_install_packages "${REQUIRED_ADDITIONAL_PACKAGES} ${RECOMMENDED_ADDITIONAL_PACKAGES}" || return $?
    return 0
}

## @brief Собрать qemu из исходников
## @details Версия 10.2.0
## @retval 0 - успешно
function qemu_build_from_sources() {
    local PACKAGE_NAME="qemu"
    local DOWNLOAD_URL="https://gitlab.com/qemu-project/${PACKAGE_NAME}.git"
    local INSTALL_DIR_PATH="${GLOBAL_CONFIG_OPT_DIR_PATH}/${PACKAGE_NAME}/src"
    local BUILD_DIR_PATH="${GLOBAL_CONFIG_OPT_DIR_PATH}/${PACKAGE_NAME}/build"
    local PROJECT_TAG="v10.2.0"

    qemu_build_setup_dependencies || return $?

    git_clone_or_fetch "${DOWNLOAD_URL}" "${INSTALL_DIR_PATH}" "${PROJECT_TAG}" || return $?

    local PIP_REQUIREMENTS_FILE_PATH="${BUILD_DIR_PATH}/requirements.txt"
    fs_create_file "tomli" "${PIP_REQUIREMENTS_FILE_PATH}" "" "rewrite_if_exist" || return $?
    pip_install_packages "${BUILD_DIR_PATH}" || return $?

    pushd "${BUILD_DIR_PATH}" || return $?
    python_venv_activate "${BUILD_DIR_PATH}" &&
    "${INSTALL_DIR_PATH}/configure"          &&
    make -j"$(nproc --all)"
    local COMMAND_CHAIN_RESULT=$?
    popd
    python_venv_deactivate
    return ${COMMAND_CHAIN_RESULT}
}

## @brief Установить умолчательный qemu
## @retval 0 - успешно
function qemu_setup_default() {
    local PACKAGE_LIST="qemu-system swtpm"
    if is_termux; then
        PACKAGE_LIST="qemu-system-x86-64 swtpm"
    elif is_msys; then
        PACKAGE_LIST="${GLOBAL_CONFIG_MSYS2_PACKAGE_PREFIX}qemu"
    fi

    package_manager_install_packages "${PACKAGE_LIST}" || return $?
    return 0
}

## @brief Установить qemu
## @retval 0 - успешно
function qemu_setup() {
    qemu_setup_default || return $?
    return 0
}