#!/bin/bash

## @brief Функции работы с VfioIgdPkg
## @details Осуществляется сборка для архитектуры X64, так заложено в оригинальном проекте https://github.com/tomitamoeko/VfioIgdPkg/blob/master/build.sh#L16
##          Т.е. запуск 32-ух битных ОС будет недоступен
## https://github.com/tomitamoeko/VfioIgdPkg


## @brief Получить путь до видеобиоса для виртуальный машины qemu + uefi (ovmf)
## @return Путь до видеобиоса для виртуальный машины qemu + uefi (ovmf)
## @retval 0 - успешно
function vfio_igd_get_vbios_path() {
   echo "${GLOBAL_CONFIG_DATA_DIR_PATH}/ovmf/x64/vbios.rom"
   return 0
}

## @brief Собрать и установить VfioIgdPkg
## @details Конечный продукт - видеобиос для виртуальный машины qemu
## @param [in] Путь до директории проекта EDK2
## @param [in] PCI ProductId целевой видеокарты (VGA) Intel
## @param [in] Путь до файла IntelGopDriver, необязательный аргумент
## @retval 0 - успешно
function vfio_igd_setup() {
    local EDK2_DIR_PATH="${1}"
    local VGA_PID="${2}"
    local INTEL_GOP_DRIVER_FILE_PATH="${3}"

    local PACKAGE_NAME="VfioIgdPkg"
    local DOWNLOAD_URL="https://github.com/tomitamoeko/${PACKAGE_NAME}.git"
    local INSTALL_DIR_PATH="${GLOBAL_CONFIG_OPT_DIR_PATH}/${PACKAGE_NAME}"
    local SYMLINK_DIR_PATH="${EDK2_DIR_PATH}/${PACKAGE_NAME}"
    local PROJECT_BRANCH="remotes/origin/master"
    local OUT_VBIOS_FILE_PATH=""
    OUT_VBIOS_FILE_PATH=$(vfio_igd_get_vbios_path) || return $?

    git_clone_or_fetch "${DOWNLOAD_URL}" "${INSTALL_DIR_PATH}" "${PROJECT_BRANCH}" || return $?

    fs_make_dirs "$(dirname "${OUT_VBIOS_FILE_PATH}")" || return $?

    fs_create_symlink "${INSTALL_DIR_PATH}" "${SYMLINK_DIR_PATH}" || return $?

    pushd "${INSTALL_DIR_PATH}" || return $?
    if [[ -e "${INTEL_GOP_DRIVER_FILE_PATH}" ]]; then
        ./build.sh --device_id "${VGA_PID}" --release --gop "${INTEL_GOP_DRIVER_FILE_PATH}" "${OUT_VBIOS_FILE_PATH}"
    else
        ./build.sh --device_id "${VGA_PID}" --release "${OUT_VBIOS_FILE_PATH}"
    fi
    local COMMAND_CHAIN_RESULT=$?
    popd
    return ${COMMAND_CHAIN_RESULT}
}
