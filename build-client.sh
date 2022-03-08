#!/bin/bash

# Основополагающая статья
# https://losst.ru/nastrojka-openvpn-v-ubuntu

#
# Setup parameters
#

MY_DIR="$(dirname "$(readlink -f "$0")")"

. "${MY_DIR}/open-vpn.config.sh"

if [ -z "$1" ]; then
  echo "User name not set"
  return 1
fi

USER_NAME="$1"

build_certificates_for_open_vpn_client() {
  pushd "${EASY_RSA_CONFIG_DIR}" || return $?

  echo "[1.1] EasyRSA build-client-full"

  ${EASY_RSA_SCRIPT_PATH} build-client-full "${USER_NAME}" nopass || return $?

  echo "[1.1] EasyRSA build-client-full: OK"

  echo "[1.2] Copy keys for OpenVPN client"

  mkdir -p "${OPEN_VPN_CLIENT_KEYS_DIR}/"

  ${COPY} "${EASY_RSA_PKI_DIR}/issued/${USER_NAME}.crt" "${OPEN_VPN_CLIENT_KEYS_DIR}/"
  ${COPY} "${EASY_RSA_PKI_DIR}/private/${USER_NAME}.key" "${OPEN_VPN_CLIENT_KEYS_DIR}/"

  echo "[1.2] Copy keys for OpenVPN client: OK"

  popd

  return 0
}

echo "[1] Build certificates for OpenVPN client \"${USER_NAME}\""

build_certificates_for_open_vpn_client || return $?

echo "[1] Build certificates for OpenVPN client \"${USER_NAME}\": OK"
