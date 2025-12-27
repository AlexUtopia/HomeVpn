#!/bin/bash

## @brief Переменные конфигурации разворота проекта

## @brief Конфигурация пакетов
GLOBAL_CONFIG_SETUP_PACKAGES_MODE="full" # min, dev, full

## @brief Конфигурация пути до корня файловой системы
GLOBAL_CONFIG_ROOT_PATH=""
if is_termux; then
    GLOBAL_CONFIG_ROOT_PATH="${PREFIX}/.."
fi

## @brief Конфигурация пути до директории usr
GLOBAL_CONFIG_USR_DIR_PATH="/usr"
if is_termux; then
    GLOBAL_CONFIG_USR_DIR_PATH="${PREFIX}"
fi

## @brief Конфигурация пути до директории etc
GLOBAL_CONFIG_ETC_DIR_PATH="/etc"
if is_termux; then
    GLOBAL_CONFIG_ETC_DIR_PATH="${GLOBAL_CONFIG_USR_DIR_PATH}/etc"
fi

## @brief Конфигурация пути до директории opt
GLOBAL_CONFIG_OPT_DIR_PATH="/opt"
if is_termux; then
    GLOBAL_CONFIG_OPT_DIR_PATH="${GLOBAL_CONFIG_USR_DIR_PATH}/opt"
fi

## @brief Имя пользователя от которого будет работать VNC сервер
## @details В Android/termux переменная окружения USER не установлена
GLOBAL_CONFIG_VNC_SERVER_USER=$(logname)
if [[ -z "${GLOBAL_CONFIG_VNC_SERVER_USER}" ]]; then
    echo "[FATAL] GLOBAL_CONFIG_VNC_USER parameter IS NOT SET"
    exit 1
fi

## @brief Имя пользователя от которого будет работать SMB сервер
## @details В Android/termux переменная окружения USER не установлена
GLOBAL_CONFIG_SMB_SERVER_USER=$(logname)
if [[ -z "${GLOBAL_CONFIG_SMB_SERVER_USER}" ]]; then
    echo "[FATAL] GLOBAL_CONFIG_SMB_SERVER_USER parameter IS NOT SET"
    exit 1
fi

## @brief Путь до публичной директории SMB сервера
GLOBAL_CONFIG_SMB_SERVER_PUBLIC_DIR_PATH="${GLOBAL_CONFIG_ROOT_PATH}/smb_share_public"
if is_msys; then
    GLOBAL_CONFIG_SMB_SERVER_PUBLIC_DIR_PATH="${SYSTEMDRIVE}/smb_share_public"
fi

## @brief TCP порты на которых работает SMB сервер
## @details https://unlix.ru/%D0%BD%D0%B0%D1%81%D1%82%D1%80%D0%BE%D0%B9%D0%BA%D0%B0-%D1%84%D0%B0%D0%B5%D1%80%D0%B2%D0%BE%D0%BB%D0%B0-iptables-%D0%B4%D0%BB%D1%8F-samba/
## @details Android не может использовать порты ниже 1024, см. https://android.stackexchange.com/a/205562
GLOBAL_CONFIG_SMB_SERVER_TCP_PORTS="139 445"
if is_termux; then
    GLOBAL_CONFIG_SMB_SERVER_TCP_PORTS="1139 4445"
fi

## @brief Путь до директории данных проекта
GLOBAL_CONFIG_DATA_DIR_PATH="${HOME_VPN_PROJECT_ROOT}/data"

## @brief Префикс пакета для разворота проекта в среде MSYS2
GLOBAL_CONFIG_MSYS2_PACKAGE_PREFIX="${MINGW_PACKAGE_PREFIX}-"