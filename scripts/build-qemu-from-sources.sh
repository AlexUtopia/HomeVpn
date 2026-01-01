#!/bin/bash

## @brief Собрать и установить qemu


# set -x # Раскомментировать для отладки

HOME_VPN_PROJECT_ROOT="$(dirname "$(readlink -f "${0}")")/.."

source "${HOME_VPN_PROJECT_ROOT}/lib/bash/os.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/config.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/bash.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/fs.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/git.include.sh"

source "${HOME_VPN_PROJECT_ROOT}/lib/bash/package_manager.include.sh"

source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/python.include.sh"

source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/qemu.include.sh"


qemu_build_from_sources