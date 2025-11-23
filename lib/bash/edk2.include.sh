#!/bin/bash

## @brief Функции работы с edk2/ovmf
## @details Результат (относительно корня проекта):
##          data/ovmf/
##             x64/
##               OVMF_CODE.fd
##               OVMF_VARS.fd
##               OVMF_CODE.secboot.fd - пригодно для запуска Windows в защищённом режиме
##               OVMF_VARS.secboot.fd - пригодно для запуска Windows в защищённом режиме
##               vbios.rom            - видеобиос (UEFI) для встроенных VGA Intel
##               IntelGopDriver.efi   - IntelGopDriver извлечённый из оригинального UEFI, необязательный
##             aarch64/
##               OVMF_CODE.fd
##               OVMF_VARS.fd
##               OVMF_CODE.secboot.fd
##               OVMF_VARS.secboot.fd
##
## https://github.com/tianocore/edk2/tree/master/OvmfPkg
## https://github.com/retrage/edk2-nightly


EDK2_TOOLCHAIN="GCC"
EDK2_BUILD_VARIANT="RELEASE"

# fixme utopia Добавить сборку secure boot
# https://superuser.com/questions/1660806/how-to-install-a-windows-guest-in-qemu-kvm-with-secure-boot-enabled
# https://github.com/rhuefi/qemu-ovmf-secureboot
# https://forums.unraid.net/topic/128595-secure-boot-off-in-ovmf-tpm-bios-windows-11/
# https://projectacrn.github.io/1.6/tutorials/waag-secure-boot.html#generate-platform-key-pk
# https://docs.fedoraproject.org/en-US/quick-docs/uefi-with-qemu/


## @brief Установить пакеты требуемые для сборки edk2/ovmf
## @retval 0 - успешно
function edk2_install_dependencies() {
    # fixme utopia Зависимости только для Ubuntu/LinuxMint
    package_manager_install_packages "build-essential uuid-dev nasm iasl" || return $?
    return 0
}

## @brief Собрать edk2/ovmf для платформы IBM PC
## @param [in] Путь до проекта edk2
## @param [in] Уникальное название сборочной директории
## @param [in] Путь до файла проекта (dsc файл)
## @param [in] Архитектуры для сборки
## @param [in] Итоговая архитектура
## @retval 0 - успешно
function edk2_ovmf_build_for_ibm_pc() {
    local EDK2_DIR_PATH="${1}"
    local BUILD_DIR_NAME="${2}"
    local PLATFORM_FILE_PATH="${3}"
    local INPUT_ARCH_LIST="${4}"
    local OUTPUT_ARCH="${5}"

    local EDK2_BUILD_DIR_PATH="${EDK2_DIR_PATH}/Build/${BUILD_DIR_NAME}/${EDK2_BUILD_VARIANT}_${EDK2_TOOLCHAIN}"
    local EDK2_OVMF_CODE_FILE_PATH="${EDK2_BUILD_DIR_PATH}/FV/OVMF_CODE.fd"
    local EDK2_OVMF_VARS_FILE_PATH="${EDK2_BUILD_DIR_PATH}/FV/OVMF_VARS.fd"
    # Опции выбраны как в сборочном скрипте пакета ovmf Ubuntu
    # https://launchpad.net/ubuntu/questing/+package/ovmf
    # https://launchpad.net/ubuntu/+source/edk2/2025.02-8ubuntu3
    local EDK2_BUILD_FLAGS=-DNETWORK_HTTP_BOOT_ENABLE=TRUE \
                           -DNETWORK_IP6_ENABLE=TRUE \
                           -DNETWORK_TLS_ENABLE \
                           -DSECURE_BOOT_ENABLE=TRUE \
                           -DTPM2_ENABLE=TRUE

    local OUT_OVMF_CODE_FILE_PATH="${GLOBAL_CONFIG_DATA_DIR_PATH}/ovmf/${OUTPUT_ARCH}/OVMF_CODE.fd"
    local OUT_OVMF_VARS_FILE_PATH="${GLOBAL_CONFIG_DATA_DIR_PATH}/ovmf/${OUTPUT_ARCH}/OVMF_VARS.fd"

    fs_make_dirs "$(dirname "${OUT_OVMF_CODE_FILE_PATH}")" || return $?

    build \
        ${EDK2_BUILD_FLAGS} \
        --platform="${PLATFORM_FILE_PATH}" \
        printf " --arch=%s" ${INPUT_ARCH_LIST} \
        --tagname="${EDK2_TOOLCHAIN}" \
        --buildtarget="${EDK2_BUILD_VARIANT}" || return $?

    cp -f "${EDK2_OVMF_CODE_FILE_PATH}" "${OUT_OVMF_CODE_FILE_PATH}" || return $?
    cp -f "${EDK2_OVMF_VARS_FILE_PATH}" "${OUT_OVMF_VARS_FILE_PATH}" || return $?
    return 0
}

## @brief Собрать edk2/ovmf для архитектуры x64
## @details Загрузка 32-ух битных ОС не поддерживается
## @param [in] Путь до проекта edk2
## @retval 0 - успешно
function edk2_ovmf_build_x64() {
    local EDK2_DIR_PATH="${1}"

    local BUILD_DIR_NAME="OvmfX64"
    local PLATFORM_FILE_PATH="${EDK2_DIR_PATH}/OvmfPkg/OvmfPkgX64.dsc"
    local INPUT_ARCH_LIST="X64"
    local OUTPUT_ARCH="x64"

    edk2_ovmf_build_for_ibm_pc "${EDK2_DIR_PATH}" "${BUILD_DIR_NAME}" "${PLATFORM_FILE_PATH}" "${INPUT_ARCH_LIST}" "${OUTPUT_ARCH}" || return $?
    return 0
}

## @brief Собрать edk2/ovmf для архитектуры x86_64
## @param [in] Путь до проекта edk2
## @retval 0 - успешно
function edk2_ovmf_build_x86_64() {
    local EDK2_DIR_PATH="${1}"

    local BUILD_DIR_NAME="Ovmf3264"
    local PLATFORM_FILE_PATH="${EDK2_DIR_PATH}/OvmfPkg/OvmfPkgIa32X64.dsc"
    local INPUT_ARCH_LIST="IA32 X64"
    local OUTPUT_ARCH="x86_64"

    edk2_ovmf_build_for_ibm_pc "${EDK2_DIR_PATH}" "${BUILD_DIR_NAME}" "${PLATFORM_FILE_PATH}" "${INPUT_ARCH_LIST}" "${OUTPUT_ARCH}" || return $?
    return 0
}

## @brief Собрать и установить edk2/ovmf
## @param [in] PCI PID (Product IDentifier) целевого VGA (Video Graphics Adapter)
## @param [in] Путь до UEFI образа материнской платы, необязательный аргумент. Если не задан то видеобиос будет собран без поддержки вывода на изображения на монитор
## @retval 0 - успешно
function edk2_ovmf_setup() {
    local VGA_PID="${1}"
    local UEFI_IMAGE_FILE_PATH="${2}"

    local PACKAGE_NAME="edk2"
    local DOWNLOAD_URL="https://github.com/tianocore/${PACKAGE_NAME}.git"
    local INSTALL_DIR_PATH="${GLOBAL_CONFIG_OPT_DIR_PATH}/${PACKAGE_NAME}"
    local PROJECT_TAG="edk2-stable202508.01"

    edk2_install_dependencies || return $?

    git_clone_or_fetch "${DOWNLOAD_URL}" "${INSTALL_DIR_PATH}" "${PROJECT_TAG}" || return $?

    pushd "${INSTALL_DIR_PATH}" || return $?

    local INTEL_GOP_DRIVER_FILE_PATH="${GLOBAL_CONFIG_DATA_DIR_PATH}/ovmf/x64/IntelGopDriver.efi"
    if [[ -e "${UEFI_IMAGE_FILE_PATH}" ]]; then
        uefiextract_setup || return $?
        uefiextract_get_intel_gop_driver "${UEFI_IMAGE_FILE_PATH}" "${INTEL_GOP_DRIVER_FILE_PATH}" || return $?
    fi

    git submodule update --init --recursive                                               &&
    pip_install_packages "${INSTALL_DIR_PATH}" "${INSTALL_DIR_PATH}/pip-requirements.txt" &&
    python_venv_activate "${INSTALL_DIR_PATH}"                                            &&
    make -C "${INSTALL_DIR_PATH}/BaseTools"                                               &&
    source edksetup.sh                                                                    &&
    edk2_ovmf_build_x64 "${INSTALL_DIR_PATH}"                                             &&
    vfio_igd_pkg_setup "${INSTALL_DIR_PATH}" "${VGA_PID}" "${INTEL_GOP_DRIVER_FILE_PATH}" &&
    python_venv_deactivate
    local COMMAND_CHAIN_RESULT=$?
    popd
    return ${COMMAND_CHAIN_RESULT}
}