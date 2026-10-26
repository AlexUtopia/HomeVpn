#!/bin/bash

# @file connect_to_host_over_ssh.sh
# @brief Подключиться к удалённому ПК по ssh
# @description
# С возможностью запускать графические приложения в том числе от имени администратора (root)
# https://www.simplified.guide/ssh/x11-forwarding-as-root


REMOTE_HOST="192.168.0.43"
USER_NAME="galina"

ssh -t -XC "${USER_NAME}@${REMOTE_HOST}" \
    'echo "Enter root password for run X11 over current ssh session from root user"; \
     sudo xauth add "$(xauth list "${DISPLAY}")"; \
     "${SHELL}" --login'