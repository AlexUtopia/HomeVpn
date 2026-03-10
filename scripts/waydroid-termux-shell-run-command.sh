#!/bin/bash

## @brief Выполнить команду в termux (bash), termux запущен в waydroid (контейнере)
## @details Запускать скрипт от обычного пользователя.
##          Для работы с waydroid shell понадобятся права администратора (суперпользователя).
##          Для копирования публичного ssh ключа в termux ssh сервер понадобятся права администратора (суперпользователя)
## @details Если установлена переменная окружения WAYDROID_TRY_RUN_COMMAND_OVER_SSH
##          то осуществляется попытка выполнить целевую команду по ssh без предварительного запуска
##          waydroid. Пример:
##          1. Запустить waydroid + termux + ssh сервер с возможностью новых ssh подключений.
##             Также здесь будет активировано ssh подключение где будет безусловно запущен bash
##               ./waydroid-termux-shell-run-command.sh "bash"
##          2. Дождаться запуска (1), запуск может занять до 3-ёх минут
##          3. Выполнить по ssh целевую команду в termux (в новой вкладке терминала), например "uname -a"
##               WAYDROID_TRY_RUN_COMMAND_OVER_SSH= ./waydroid-termux-shell-run-command.sh "uname -a"

HOME_VPN_PROJECT_ROOT="$(dirname "$(readlink -f "${0}")")/.."

source "${HOME_VPN_PROJECT_ROOT}/lib/bash/os.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/config.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/bash.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/fs.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/git.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/download.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/user.include.sh"

source "${HOME_VPN_PROJECT_ROOT}/lib/bash/termux.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/ssh_client.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/waydroid.include.sh"


if [[ -v WAYDROID_TRY_RUN_COMMAND_OVER_SSH ]]; then
    waydroid_termux_shell_try_run_command_over_ssh "$*"
else
    waydroid_termux_shell_run_command "$*"
fi
