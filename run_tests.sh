#!/bin/bash

MY_DIR="$(dirname "$(readlink -f "$0")")"

python3.11 -m unittest "${MY_DIR}/main.py"