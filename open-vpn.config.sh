#!/bin/bash

#
# Setup parameters
#

MY_DIR="$(dirname "$(readlink -f "$0")")"

GET_CONFIG_PARAMETER_COMMAND="python3.8 ${MY_DIR}/main.py config"

export COPY="cp -f"

export OPEN_VPN_SERVER_NAME=$(${GET_CONFIG_PARAMETER_COMMAND} open_vpn_server_name)
export OPEN_VPN_KEYS_DIR=$(${GET_CONFIG_PARAMETER_COMMAND} open_vpn_keys_dir)
export OPEN_VPN_CLIENT_KEYS_DIR=$(${GET_CONFIG_PARAMETER_COMMAND} open_vpn_client_keys_dir)
export EASY_RSA_VERSION=$(${GET_CONFIG_PARAMETER_COMMAND} easy_rsa_version)
export EASY_RSA_CONFIG_DIR=$(${GET_CONFIG_PARAMETER_COMMAND} easy_rsa_config_dir)
export EASY_RSA_PKI_DIR=$(${GET_CONFIG_PARAMETER_COMMAND} easy_rsa_pki_dir)
export EASY_RSA_SCRIPT_PATH=$(${GET_CONFIG_PARAMETER_COMMAND} easy_rsa_script_path)
export WATCHDOG_USER_NAME=$(${GET_CONFIG_PARAMETER_COMMAND} watchdog_user_name)
