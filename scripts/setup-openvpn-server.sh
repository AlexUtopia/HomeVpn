#!/bin/bash

## @brief Установить и настроить систему сертификации для openvpn сервера


# set -x # Раскомментировать для отладки

HOME_VPN_PROJECT_ROOT="$(dirname "$(readlink -f "${0}")")/.."

source "${HOME_VPN_PROJECT_ROOT}/lib/bash/os.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/config.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/bash.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/fs.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/download.include.sh"

source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/easyrsa.include.sh"

source "${HOME_VPN_PROJECT_ROOT}/lib/bash/project_config.include.sh"


easyrsa_setup