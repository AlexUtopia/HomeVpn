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

download_easy_rsa() {
  local DOWNLOAD_DIR=$1

  local EASY_RSA_DOWNLOAD_FILE="EasyRSA-${EASY_RSA_VERSION}.tgz"
  local EASY_RSA_DOWNLOAD_URL="https://github.com/OpenVPN/easy-rsa/releases/download/v${EASY_RSA_VERSION}/${EASY_RSA_DOWNLOAD_FILE}"
  local EASY_RSA_DOWNLOADED_FILE_PATH="${DOWNLOAD_DIR}/${EASY_RSA_DOWNLOAD_FILE}"

  wget -O "${EASY_RSA_DOWNLOADED_FILE_PATH}" -N ${EASY_RSA_DOWNLOAD_URL}
  if [ $? -ne 0 ]; then
    return $?
  fi

  tar --strip-components=1 -C "${DOWNLOAD_DIR}" -xvf "${EASY_RSA_DOWNLOADED_FILE_PATH}"
  if [ $? -ne 0 ]; then
    return $?
  fi

  return 0
}

setup_ca() {
  cd "${EASY_RSA_CONFIG_DIR}" || return $?

  echo "[2.1] EasyRSA init-pki"

  ${EASY_RSA_SCRIPT_PATH} init-pki
  if [ $? -ne 0 ]; then
    return $?
  fi

  echo "[2.1] EasyRSA init-pki: OK"

  echo "[2.2] EasyRSA build-ca"

  ${EASY_RSA_SCRIPT_PATH} build-ca
  if [ $? -ne 0 ]; then
    return $?
  fi

  echo "[2.2] EasyRSA build-ca: OK"

  echo "[2.3] EasyRSA gen-dh"

  ${EASY_RSA_SCRIPT_PATH} gen-dh
  if [ $? -ne 0 ]; then
    return $?
  fi

  echo "[2.3] EasyRSA gen-dh: OK"

  echo "[2.4] OpenVPN generate HMAC key for TLS authentication"

  openvpn --genkey --secret "${EASY_RSA_PKI_DIR}/ta.key"
  if [ $? -ne 0 ]; then
    return $?
  fi

  echo "[2.4] OpenVPN generate HMAC key for TLS authentication: OK"

  echo "[2.5] EasyRSA gen-crl"

  ${EASY_RSA_SCRIPT_PATH} gen-crl
  if [ $? -ne 0 ]; then
    return $?
  fi

  echo "[2.5] EasyRSA gen-crl: OK"

  return 0
}

build_certificates_for_open_vpn_server() {
  cd "${EASY_RSA_CONFIG_DIR}" || return $?

  echo "[3.1] EasyRSA build-server-full"

  ${EASY_RSA_SCRIPT_PATH} build-server-full "${OPEN_VPN_SERVER_NAME}" nopass
  if [ $? -ne 0 ]; then
    return $?
  fi

  echo "[3.1] EasyRSA build-server-full: OK"

  echo "[3.2] Copy keys for OpenVPN server"

  cp "${EASY_RSA_PKI_DIR}/ca.crt" "${OPEN_VPN_CONFIG_DIR}/"
  cp "${EASY_RSA_PKI_DIR}/dh.pem" "${OPEN_VPN_CONFIG_DIR}/"
  cp "${EASY_RSA_PKI_DIR}/crl.pem" "${OPEN_VPN_CONFIG_DIR}/"
  cp "${EASY_RSA_PKI_DIR}/ta.key" "${OPEN_VPN_CONFIG_DIR}/"
  cp "${EASY_RSA_PKI_DIR}/issued/${OPEN_VPN_SERVER_NAME}.crt" "${OPEN_VPN_CONFIG_DIR}/"
  cp "${EASY_RSA_PKI_DIR}/private/${OPEN_VPN_SERVER_NAME}.key" "${OPEN_VPN_CONFIG_DIR}/"

  echo "[3.2] Copy keys for OpenVPN server: OK"

  return 0
}

mkdir -p ${EASY_RSA_CONFIG_DIR}

echo "[1] Download easy-rsa"

download_easy_rsa ${EASY_RSA_CONFIG_DIR}
if [ $? -ne 0 ]; then
  return $?
fi

echo "[1] Download easy-rsa: OK"

echo "[2] Setup CA"

setup_ca
if [ $? -ne 0 ]; then
  return $?
fi

echo "[2] Setup CA: OK"

echo "[3] Build certificates for OpenVPN server"

build_certificates_for_open_vpn_server

if [ $? -ne 0 ]; then
  return $?
fi

echo "[3] Build certificates for OpenVPN server: OK"
