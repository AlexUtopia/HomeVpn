#!/bin/bash

## @brief Включение умолчательного или пользовательского (альтернативного) конфига экземпляра проекта


if [[ -z "${CONFIG_PROJECT_INSTANCE_FILE_PATH}" ]]; then
    CONFIG_PROJECT_INSTANCE_FILE_PATH="${HOME_VPN_PROJECT_ROOT}/project.default.config.sh"
fi
source "${CONFIG_PROJECT_INSTANCE_FILE_PATH}"