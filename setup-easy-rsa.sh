#!/bin/bash

# Основополагающая статья
# https://losst.ru/nastrojka-openvpn-v-ubuntu

#
# Setup parameters
#

MY_DIR="$(dirname "$(readlink -f "$0")")"

. "${MY_DIR}/open-vpn.config.sh"

download_easy_rsa() {
  local DOWNLOAD_DIR=$1

  local EASY_RSA_DOWNLOAD_FILE="EasyRSA-${EASY_RSA_VERSION}.tgz"
  local EASY_RSA_DOWNLOAD_URL="https://github.com/OpenVPN/easy-rsa/releases/download/v${EASY_RSA_VERSION}/${EASY_RSA_DOWNLOAD_FILE}"
  local EASY_RSA_DOWNLOADED_FILE_PATH="${DOWNLOAD_DIR}/${EASY_RSA_DOWNLOAD_FILE}"

  wget -O "${EASY_RSA_DOWNLOADED_FILE_PATH}" -N "${EASY_RSA_DOWNLOAD_URL}" || return $?

  tar --strip-components=1 -C "${DOWNLOAD_DIR}" -xvf "${EASY_RSA_DOWNLOADED_FILE_PATH}" || return $?

  return 0
}

setup_ca() {
  pushd "${EASY_RSA_CONFIG_DIR}" || return $?

  echo "[2.1] EasyRSA init-pki"

  ${EASY_RSA_SCRIPT_PATH} init-pki || return $?

  echo "[2.1] EasyRSA init-pki: OK"

  echo "[2.2] EasyRSA build-ca"

  ${EASY_RSA_SCRIPT_PATH} build-ca || return $?

  echo "[2.2] EasyRSA build-ca: OK"

  echo "[2.3] EasyRSA gen-dh"

  ${EASY_RSA_SCRIPT_PATH} gen-dh || return $?

  echo "[2.3] EasyRSA gen-dh: OK"

  echo "[2.4] OpenVPN generate HMAC key for TLS authentication"

  openvpn --genkey --secret "${EASY_RSA_PKI_DIR}/ta.key" || return $?

  echo "[2.4] OpenVPN generate HMAC key for TLS authentication: OK"

  echo "[2.5] EasyRSA gen-crl"

  ${EASY_RSA_SCRIPT_PATH} gen-crl || return $?

  echo "[2.5] EasyRSA gen-crl: OK"

  popd

  return 0
}

build_certificates_for_open_vpn_server() {
  pushd "${EASY_RSA_CONFIG_DIR}" || return $?

  echo "[3.1] EasyRSA build-server-full"

  ${EASY_RSA_SCRIPT_PATH} build-server-full "${OPEN_VPN_SERVER_NAME}" nopass || return $?

  echo "[3.1] EasyRSA build-server-full: OK"

  echo "[3.2] Copy keys for OpenVPN server"

  ${COPY} "${EASY_RSA_PKI_DIR}/ca.crt" "${OPEN_VPN_KEYS_DIR}/"
  ${COPY} "${EASY_RSA_PKI_DIR}/dh.pem" "${OPEN_VPN_KEYS_DIR}/"
  ${COPY} "${EASY_RSA_PKI_DIR}/crl.pem" "${OPEN_VPN_KEYS_DIR}/"
  ${COPY} "${EASY_RSA_PKI_DIR}/ta.key" "${OPEN_VPN_KEYS_DIR}/"
  ${COPY} "${EASY_RSA_PKI_DIR}/issued/${OPEN_VPN_SERVER_NAME}.crt" "${OPEN_VPN_KEYS_DIR}/"
  ${COPY} "${EASY_RSA_PKI_DIR}/private/${OPEN_VPN_SERVER_NAME}.key" "${OPEN_VPN_KEYS_DIR}/"

  echo "[3.2] Copy keys for OpenVPN server: OK"

  popd

  return 0
}

mkdir -p "${EASY_RSA_CONFIG_DIR}"

echo "[1] Download easy-rsa"

download_easy_rsa "${EASY_RSA_CONFIG_DIR}" || exit $?

echo "[1] Download easy-rsa: OK"

echo "[2] Setup CA"

setup_ca || exit $?

echo "[2] Setup CA: OK"

echo "[3] Build certificates for OpenVPN server"

build_certificates_for_open_vpn_server || exit $?

echo "[3] Build certificates for OpenVPN server: OK"
