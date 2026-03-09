#!/bin/bash

## @brief Выполнить команду в termux (bash), termux запущен в waydroid (контейнере)
## @details Запускать скрипт от обычного пользователя.
##          Для работы с waydroid shell понадобятся права администратора (суперпользователя).
##          Для копирования публичного ssh ключа в termux ssh сервер понадобятся права администратора (суперпользователя)


HOME_VPN_PROJECT_ROOT="$(dirname "$(readlink -f "${0}")")/.."

source "${HOME_VPN_PROJECT_ROOT}/lib/bash/os.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/config.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/bash.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/fs.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/git.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/download.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/user.include.sh"

source "${HOME_VPN_PROJECT_ROOT}/lib/bash/termux.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/waydroid.include.sh"


waydroid_termux_shell_run_command "$*"
