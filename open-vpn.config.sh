#!/bin/bash

#
# Setup parameters
#

MY_DIR="$(dirname "$(readlink -f "${0}")")"

export COPY="cp -f"

export OPEN_VPN_SERVER_NAME="$("${MY_DIR}/run_cmd.sh" config open_vpn_server_name)"
export OPEN_VPN_KEYS_DIR="$("${MY_DIR}/run_cmd.sh" config open_vpn_keys_dir)"
export OPEN_VPN_CLIENT_KEYS_DIR="$("${MY_DIR}/run_cmd.sh" config open_vpn_client_keys_dir)"
export EASY_RSA_VERSION="$("${MY_DIR}/run_cmd.sh" config easy_rsa_version)"
export EASY_RSA_CONFIG_DIR="$("${MY_DIR}/run_cmd.sh" config easy_rsa_config_dir)"
export EASY_RSA_PKI_DIR="$("${MY_DIR}/run_cmd.sh" config easy_rsa_pki_dir)"
export EASY_RSA_SCRIPT_PATH="$("${MY_DIR}/run_cmd.sh" config easy_rsa_script_path)"
