#!/bin/sh

# Основополагающая статья
# https://losst.ru/nastrojka-openvpn-v-ubuntu

#
# Setup parameters
#

OPEN_VPN_CONFIG_DIR="/etc/openvpn"
EASY_RSA_CONFIG_DIR="${OPEN_VPN_CONFIG_DIR}/easy-rsa"
EASY_RSA_PKI_DIR="${EASY_RSA_CONFIG_DIR}/pki"
EASY_RSA_VERSION="3.0.8"

EASY_RSA_SCRIPT_PATH="${EASY_RSA_CONFIG_DIR}/easyrsa"
OPEN_VPN_SERVER_NAME="HomeVpn"

USER_NAME="TestUser22"

build_certificates_for_open_vpn_client() {
  cd "${EASY_RSA_CONFIG_DIR}" || return $?

  # fixme utopia Проверить пользователя на существование

  echo "[1.1] EasyRSA build-client-full"

  ${EASY_RSA_SCRIPT_PATH} build-client-full "${USER_NAME}" nopass || return $?

  echo "[1.1] EasyRSA build-client-full: OK"

  echo "[1.2] Copy keys for OpenVPN client"

  cp "${EASY_RSA_PKI_DIR}/issued/${USER_NAME}.crt" "${OPEN_VPN_CONFIG_DIR}/client/"
  cp "${EASY_RSA_PKI_DIR}/private/${USER_NAME}.key" "${OPEN_VPN_CONFIG_DIR}/client/"

  echo "[1.2] Copy keys for OpenVPN client: OK"

  return 0
}

echo "[1] Build certificates for OpenVPN client \"${USER_NAME}\""

build_certificates_for_open_vpn_client || return $?

echo "[1] Build certificates for OpenVPN client \"${USER_NAME}\": OK"
