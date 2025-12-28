#!/bin/bash

## @brief Скрипт для запуска юнит-тестов проекта


HOME_VPN_PROJECT_ROOT="$(dirname "$(readlink -f "${0}")")"

source "${HOME_VPN_PROJECT_ROOT}/lib/bash/os.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/config.include.sh"

source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/python.include.sh"

python_venv_activate "${HOME_VPN_PROJECT_ROOT}" &&
python -m unittest "${HOME_VPN_PROJECT_ROOT}/main.py"
COMMAND_CHAIN_RESULT=$?
python_venv_deactivate
exit ${COMMAND_CHAIN_RESULT}