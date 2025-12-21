#!/bin/bash

## @brief Функции работы со службами
##        1) [Linux]          systemd
##        2) [Android/termux] runit
##        3) [Windows/MSYS2]  cygrunsrv (неготов)
##        4) [Windows]        sc (неготов)


## @brief Инициализировать службы
## @retval 0 - успешно
function service_setup() {
    if is_termux; then
        runit_setup || return $?
        return 0
    elif is_msys; then
        return 0
    fi

    systemd_setup || return $?
    return 0
}

## @brief Проверить запущена ли служба
## @param [in] Имя службы
## @param [in] Имя пользователя, необязательный аргумент
##             - если не задано, то действие для системной службы
##             - если задано, то действие для пользовательской службы
## @retval 0 - служба запущена; 1 - нет
function service_is_active() {
    local SERVICE_NAME="${1}"
    local USER_NAME="${2}"

    if is_termux; then
        runit_service_is_active "${SERVICE_NAME}" || return $?
        return 0
    elif is_msys; then
        return 0
    fi

    systemd_service_is_active "${SERVICE_NAME}" "${USER_NAME}" || return $?
    return 0
}

## @brief Добавить службу в автозапуск (при старте ОС) и запустить
## @param [in] Имя службы
## @param [in] Имя пользователя, необязательный аргумент
##             - если не задано, то действие для системной службы
##             - если задано, то действие для пользовательской службы
## @retval 0 - успешно
function service_enable() {
    local SERVICE_NAME="${1}"
    local USER_NAME="${2}"

    if is_termux; then
        runit_service_enable "${SERVICE_NAME}" || return $?
        return 0
    elif is_msys; then
        return 0
    fi

    systemd_service_enable "${SERVICE_NAME}" "${USER_NAME}" || return $?
    return 0
}

## @brief Остановить службу и убрать её из автозапуска (при старте ОС)
## @param [in] Имя службы
## @param [in] Имя пользователя, необязательный аргумент
##             - если не задано, то действие для системной службы
##             - если задано, то действие для пользовательской службы
## @retval 0 - успешно
function service_disable() {
    local SERVICE_NAME="${1}"
    local USER_NAME="${2}"

    if is_termux; then
        runit_service_disable "${SERVICE_NAME}" || return $?
        return 0
    elif is_msys; then
        return 0
    fi

    systemd_service_disable "${SERVICE_NAME}" "${USER_NAME}" || return $?
    return 0
}