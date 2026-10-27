#!/bin/bash

# @file run-static-analysis.sh
# @brief Запустить статические анализаторы mypy и pylint


# set -x # Раскомментировать для отладки

HOME_VPN_PROJECT_ROOT="$(dirname "$(readlink -f "${0}")")/.."

source "${HOME_VPN_PROJECT_ROOT}/lib/bash/os.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/config.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/bash.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/fs.include.sh"

source "${HOME_VPN_PROJECT_ROOT}/lib/bash/package_manager.include.sh"

source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/python.include.sh"


pushd "${HOME_VPN_PROJECT_ROOT}" || exit $?

python_venv_activate "${HOME_VPN_PROJECT_ROOT}" || exit $?

COMMAND_CHAIN_RESULT=0

python -m mypy || COMMAND_CHAIN_RESULT=$?

python -m pylint main.py lib/python || COMMAND_CHAIN_RESULT=$?

python_venv_deactivate

popd

exit ${COMMAND_CHAIN_RESULT}
