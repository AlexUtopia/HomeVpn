#!/bin/bash

## @brief Функции работы с EasyRSA
## https://losst.ru/nastrojka-openvpn-v-ubuntu


EASYRSA_SERVER_NAME="server"


## @brief Получить путь до исполняемого файла EasyRSA
## @return Путь до исполняемого файла EasyRSA
## @retval 0 - успешно
function easyrsa_get_executable_path() {
    echo "${GLOBAL_CONFIG_OPT_DIR_PATH}/easyrsa/easyrsa"
    return 0
}

## @brief Вызвать главный скрипт EasyRSA
## @param [in] ... Прочие параметры вызова скрипта
## @retval 0 - успешно
function easyrsa_сall() {
    "$(easyrsa_get_executable_path)" --pki="${CONFIG_EASYRSA_PKI_DIR_PATH}" $@ || return $?
    return 0
}

## @brief Установить пакет EasyRSA
## @details Версия 3.2.3
## @details Установка в директорию ${GLOBAL_CONFIG_OPT_DIR_PATH}
## @retval 0 - успешно
function easyrsa_packages_setup() {
    export PACKAGE_VERSION="3.2.3"
    local DOWNLOAD_FILE="EasyRSA-${PACKAGE_VERSION}.tgz"
    local DOWNLOAD_URL="https://github.com/OpenVPN/easy-rsa/releases/download/v${PACKAGE_VERSION}/${DOWNLOAD_FILE}"
    local INSTALL_DIR_PATH=""
    INSTALL_DIR_PATH=$(dirname "$(easyrsa_get_executable_path)") || return $?

    local STRIP_COMPONENTS=1
    download_targz_and_unpack "${DOWNLOAD_URL}" "${INSTALL_DIR_PATH}" "remake_dirs" "${STRIP_COMPONENTS}" || return $?
    return 0
}

## @brief Настроить центр сертификации
## @retval 0 - успешно
function easyrsa_ca_setup() {
    fs_make_dirs "${CONFIG_EASYRSA_PKI_DIR_PATH}"                     &&
    easyrsa_сall init-pki                                             &&
    easyrsa_сall build-ca                                             &&
    easyrsa_сall gen-dh                                               &&
    openvpn --genkey --secret "${CONFIG_EASYRSA_PKI_DIR_PATH}/ta.key" &&
    easyrsa_сall gen-crl || return $?
}

## @brief Настроить сертификаты openvpn сервера
## @retval 0 - успешно
function easyrsa_build_certificates_for_openvpn_server() {
    local SERVER_NAME="${EASYRSA_SERVER_NAME}"

    fs_make_dirs "${CONFIG_OPENVPN_SERVER_DATA_DIR_PATH}" &&
    easyrsa_сall build-server-full "${SERVER_NAME}"       &&
    fs_create_symlink "${CONFIG_EASYRSA_PKI_DIR_PATH}/ca.crt" \
        "${CONFIG_OPENVPN_SERVER_DATA_DIR_PATH}/"         &&
    fs_create_symlink "${CONFIG_EASYRSA_PKI_DIR_PATH}/dh.pem" \
        "${CONFIG_OPENVPN_SERVER_DATA_DIR_PATH}/"         &&
    fs_create_symlink "${CONFIG_EASYRSA_PKI_DIR_PATH}/crl.pem" \
        "${CONFIG_OPENVPN_SERVER_DATA_DIR_PATH}/"         &&
    fs_create_symlink "${CONFIG_EASYRSA_PKI_DIR_PATH}/ta.key" \
        "${CONFIG_OPENVPN_SERVER_DATA_DIR_PATH}/"         &&
    fs_create_symlink "${CONFIG_EASYRSA_PKI_DIR_PATH}/issued/${SERVER_NAME}.crt" \
        "${CONFIG_OPENVPN_SERVER_DATA_DIR_PATH}/"         &&
    fs_create_symlink "${CONFIG_EASYRSA_PKI_DIR_PATH}/private/${SERVER_NAME}.key" \
        "${CONFIG_OPENVPN_SERVER_DATA_DIR_PATH}/" || return $?
}

## @brief Установить и настроить EasyRSA
## @retval 0 - успешно
function easyrsa_setup() {
    easyrsa_packages_setup || return $?
    easyrsa_ca_setup || return $?
    easyrsa_build_certificates_for_openvpn_server || return $?
    return 0
}

## @brief Настроить сертификаты openvpn клиента
## @param [in] Имя клиента
## @retval 0 - успешно
function easyrsa_build_certificates_for_openvpn_client() {
    local CLIENT_NAME="${1}"
    if [[ "${CLIENT_NAME}" == "${EASYRSA_SERVER_NAME}" || "${CLIENT_NAME}" == "" ]]; then
        echo "[EasyRSA] Client name \"${CLIENT_NAME}\" WRONG"
        return 1
    fi

    local CONFIG_OPENVPN_CLIENT_DATA_DIR_PATH=$(printf "${CONFIG_OPENVPN_CLIENT_DATA_DIR_PATH_TEMPLATE}" "${CLIENT_NAME}")

    fs_make_dirs "${CONFIG_OPENVPN_CLIENT_DATA_DIR_PATH}"  &&
    easyrsa_сall build-client-full "${CLIENT_NAME}" nopass &&
    fs_create_symlink "${CONFIG_EASYRSA_PKI_DIR_PATH}/issued/${CLIENT_NAME}.crt" \
        "${CONFIG_OPENVPN_CLIENT_DATA_DIR_PATH}/"          &&
    fs_create_symlink "${CONFIG_EASYRSA_PKI_DIR_PATH}/private/${CLIENT_NAME}.key" \
        "${CONFIG_OPENVPN_CLIENT_DATA_DIR_PATH}/"
    local COMMAND_CHAIN_RESULT=$?

    popd
    return ${COMMAND_CHAIN_RESULT}
}