#!/bin/bash

## @brief Функции работы с python
## https://www.python.org/
## https://docs.python.org/3/library/venv.html


## @brief Получить целевую версию python для данной платформы
## @details Для проекта требуется версия python >= 3.11 из-за использования regex atomic group
##          https://docs.python.org/3/library/re.html#regular-expression-syntax
## @return Целевая версия python для данной платформы
## @retval 0 - успешно
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

## @brief Получить путь до директории venv python проекта
## @param [in] Путь до корня python проекта
## @return Путь до директории venv python проекта
## @retval 0 - успешно
function python_venv_get_dir_path() {
    PROJECT_DIR_PATH="${1}"

    echo "${PROJECT_DIR_PATH}/.venv"
    return 0
}

## @brief Активировать venv
## @param [in] Путь до корня python проекта
## @retval 0 - успешно
function python_venv_activate() {
    local PROJECT_DIR_PATH="${1}"

    local VENV_DIR_PATH=""
    VENV_DIR_PATH=$(python_venv_get_dir_path "${PROJECT_DIR_PATH}") || return $?

    source "${VENV_DIR_PATH}/bin/activate" || return $?
    return 0
}

## @brief Деактивировать venv
## @retval 0 - успешно
function python_venv_deactivate() {
    deactivate || return $?
    return 0
}

## @brief Установить python пакеты при помощи pip в venv
## @details Пакеты форсированно переустанавливаются
## @param [in] Путь до корня python проекта
## @param [in] Путь до requirements.txt файла со списком пакетов для установки, если не задан то используется "${PROJECT_DIR_PATH}/requirements.txt"
## @retval 0 - успешно
function pip_install_packages() {
    local PROJECT_DIR_PATH="${1}"
    local REQUIREMENTS_FILE_PATH="${2}"

    if [[ -z "${REQUIREMENTS_FILE_PATH}" && -n "${PROJECT_DIR_PATH}" ]]; then
        REQUIREMENTS_FILE_PATH="${PROJECT_DIR_PATH}/requirements.txt"
    fi

    local PYTHON_EXECUTABLE="python$(python_get_version)"

    local VENV_DIR_PATH=""
    VENV_DIR_PATH="$(python_venv_get_dir_path "${PROJECT_DIR_PATH}")" || return $?

    "${PYTHON_EXECUTABLE}" -m venv "${VENV_DIR_PATH}" || return $?
    python_venv_activate "${PROJECT_DIR_PATH}" || return $?
    pip install -r "${REQUIREMENTS_FILE_PATH}" --force-reinstall --ignore-installed
    local COMMAND_CHAIN_RESULT=$?
    python_venv_deactivate
    return ${COMMAND_CHAIN_RESULT}
}

## @brief Установить python для проекта
## @retval 0 - успешно
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
