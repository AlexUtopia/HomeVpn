#!/bin/bash

## @brief Параметры настройки openvpn сервера

export HOME_VPN_PROJECT_ROOT="$(dirname "$(readlink -f "${0}")")/.."

#export OPEN_VPN_SERVER_NAME="$("${MY_DIR}/run_cmd.sh" config open_vpn_server_name)"
#export OPEN_VPN_KEYS_DIR="$("${MY_DIR}/run_cmd.sh" config open_vpn_keys_dir)"
#export OPEN_VPN_CLIENT_KEYS_DIR="$("${MY_DIR}/run_cmd.sh" config open_vpn_client_keys_dir)"
#export EASY_RSA_VERSION="$("${MY_DIR}/run_cmd.sh" config easy_rsa_version)"
#export EASY_RSA_CONFIG_DIR="$("${MY_DIR}/run_cmd.sh" config easy_rsa_config_dir)"
#export EASY_RSA_PKI_DIR="$("${MY_DIR}/run_cmd.sh" config easy_rsa_pki_dir)"
#export EASY_RSA_SCRIPT_PATH="$("${MY_DIR}/run_cmd.sh" config easy_rsa_script_path)"

# fixme achizhov instance надо передавать как параметр скрипта run_cmd.sh

export HOME_VPN_PROJECT_INSTANCE_NAME=""
HOME_VPN_PROJECT_INSTANCE_NAME="$(cat "${HOME_VPN_PROJECT_ROOT}/project_instance_name")" || "HomeVpn"
export OPENVPN_DATA_DIR_PATH="${GLOBAL_CONFIG_OPT_DIR_PATH}/${HOME_VPN_PROJECT_INSTANCE_NAME}"

export OPENVPN_SERVER_DATA_DIR_PATH="${OPENVPN_DATA_DIR_PATH}/server"
export OPENVPN_SERVER_LOG_DIR_PATH="${OPENVPN_SERVER_DATA_DIR_PATH}/logs"

export OPENVPN_CLIENT_DATA_DIR_PATH="${OPENVPN_DATA_DIR_PATH}/client"
export OPENVPN_CLIENT_LOG_DIR_PATH="${OPENVPN_CLIENT_DATA_DIR_PATH}/logs"

export EASY_RSA_VERSION="3.2.3"
export EASY_RSA_DIR_PATH="${OPENVPN_SERVER_DATA_DIR_PATH}/easy-rsa"
export EASY_RSA_PKI_DIR_PATH="${OPENVPN_SERVER_DATA_DIR_PATH}/pki"
export EASY_RSA_SCRIPT_CALL="'${EASY_RSA_DIR_PATH}/easyrsa' --pki='${EASY_RSA_PKI_DIR_PATH}'"