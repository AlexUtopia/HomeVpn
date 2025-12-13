#!/bin/bash

## @brief Установка ovmf


HOME_VPN_PROJECT_ROOT="$(dirname "$(readlink -f "${0}")")/.."

source "${HOME_VPN_PROJECT_ROOT}/lib/bash/os.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/config.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/bash.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/fs.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/download.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/apt.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/pacman.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/package_manager.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/git.include.sh"

source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/python.include.sh"

source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/uefiextract.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/vfio_igd.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/edk2.include.sh"

