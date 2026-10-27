#!/bin/bash

# @file python.include.sh
# @brief Функции работы с python
# @description
# https://www.python.org/
# https://docs.python.org/3/library/venv.html


# @description Получить целевую версию python для данной платформы
# Для проекта требуется версия python >= 3.12 из-за использования
#         [3.11+] regex atomic group
#           https://docs.python.org/3/library/re.html#regular-expression-syntax
#         [3.12+] возможность создания наследников от pathlib.Path
#           https://docs.python.org/3.12/whatsnew/3.12.html
#           The pathlib.Path class now supports subclassing
# @stdout Целевая версия python для данной платформы
# @exitcode 0 успешно
function python_get_version() {
    if package_manager_is_apt; then
        if ! is_termux; then
            echo "3.13"
            return 0
        fi
    fi
    echo "3"
    return 0
}


function python_get_executable() {
    echo "python$(python_get_version)"
    return 0
}

# @description Получить путь до директории venv python проекта
# @arg $1 string Путь до корня python проекта
# @stdout Путь до директории venv python проекта
# @exitcode 0 успешно
function python_venv_get_dir_path() {
    PROJECT_DIR_PATH="${1}"

    echo "${PROJECT_DIR_PATH}/.venv"
    return 0
}

# @description Активировать venv
# @arg $1 string Путь до корня python проекта
# @exitcode 0 успешно
function python_venv_activate() {
    local PROJECT_DIR_PATH="${1}"

    local VENV_DIR_PATH=""
    VENV_DIR_PATH=$(python_venv_get_dir_path "${PROJECT_DIR_PATH}") || return $?

    source "${VENV_DIR_PATH}/bin/activate" || return $?
    return 0
}

# @description Деактивировать venv
# @exitcode 0 успешно
function python_venv_deactivate() {
    deactivate || return $?
    return 0
}

# @description Установить python пакеты при помощи pip в venv
# @arg $1 string Путь до корня python проекта
# @arg $2 string Путь до requirements.txt файла (для сторонних проектов); если не задан, проект ставится из pyproject.toml
# @arg $3 string Дополнительные зависимости (extras) из pyproject.toml, например "dev"
# @exitcode 0 успешно
function pip_install_packages() {
    local PROJECT_DIR_PATH="${1}"
    local REQUIREMENTS_FILE_PATH="${2}"
    local EXTRAS="${3}"

    local PYTHON_EXECUTABLE="$(python_get_executable)"

    local VENV_DIR_PATH=""
    VENV_DIR_PATH="$(python_venv_get_dir_path "${PROJECT_DIR_PATH}")" || return $?

    "${PYTHON_EXECUTABLE}" -m venv "${VENV_DIR_PATH}" || return $?
    python_venv_activate "${PROJECT_DIR_PATH}" || return $?

    # pip в venv обновляем всегда: это безопасно и изолировано от системного python
    python -m pip install --upgrade pip || { python_venv_deactivate; return $?; }

    local COMMAND_CHAIN_RESULT=0
    if [[ -n "${REQUIREMENTS_FILE_PATH}" ]]; then
        # Сторонние сборки (qemu, edk2) используют собственный requirements-файл
        python -m pip install -r "${REQUIREMENTS_FILE_PATH}" --force-reinstall --ignore-installed
        COMMAND_CHAIN_RESULT=$?
    else
        local PROJECT_SPEC="${PROJECT_DIR_PATH}"
        if [[ -n "${EXTRAS}" ]]; then
            PROJECT_SPEC="${PROJECT_DIR_PATH}[${EXTRAS}]"
        fi
        python -m pip install --upgrade --editable "${PROJECT_SPEC}"
        COMMAND_CHAIN_RESULT=$?
    fi

    python_venv_deactivate
    return ${COMMAND_CHAIN_RESULT}
}

# @description Установить python для проекта
# @exitcode 0 успешно
function python_setup() {
    local PYTHON_VERSION=""
    PYTHON_VERSION=$(python_get_version) || return $?

    if package_manager_is_apt; then
        if ! is_termux; then
            # https://launchpad.net/~deadsnakes/+archive/ubuntu/ppa
            apt_add_ppa "deadsnakes/ppa" || return $?
        fi
    fi

    local PACKAGE_LIST="python${PYTHON_VERSION} python3-pip python${PYTHON_VERSION}-venv python${PYTHON_VERSION}-dev"
    if is_termux; then
        PACKAGE_LIST="python python-pip"
    elif is_msys; then
        PACKAGE_LIST="python python-pip"
    fi

    package_manager_install_packages "${PACKAGE_LIST}" || return $?

    pip_install_packages "${HOME_VPN_PROJECT_ROOT}" || return $?
    return 0
}

# @description Установить dev-зависимости python (mypy, pylint)
# @exitcode 0 успешно
function python_dev_setup() {
    pip_install_packages "${HOME_VPN_PROJECT_ROOT}" "" "dev"
    return $?
}
