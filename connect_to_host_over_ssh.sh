#!/bin/bash

HOST_IP_ADDRESS="192.168.0.148"
USER="utopia"

# https://www.simplified.guide/ssh/x11-forwarding-as-root

ssh -t -XC "${USER}"@"${HOST_IP_ADDRESS}" 'echo "Enter root password for run X11 over current ssh session from root user"; sudo xauth add `xauth list "${DISPLAY}"`; bash -l' || exit $?
