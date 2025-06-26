#!/bin/bash

MY_DIR="$(dirname "$(readlink -f "${0}")")"

VENV_DIR_PATH="${MY_DIR}/.venv"
VENV_ACTIVATE_FILE_PATH="${VENV_DIR_PATH}/bin/activate"

source "${VENV_ACTIVATE_FILE_PATH}" && python "${MY_DIR}/main.py" "$@" && deactivate || exit $?
exit 0
