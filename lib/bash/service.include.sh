#!/bin/bash

# @file service.include.sh
# @brief Функции работы со службами
# @description
#        1) [Linux]          systemd
#        2) [Android/termux] runit
#        3) [Windows/MSYS2]  cygrunsrv (неготов)
#        4) [Windows]        sc (неготов)


source "${HOME_VPN_PROJECT_ROOT}/lib/bash/service/systemd.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/service/runit.include.sh"


# @description Инициализировать службы
# @exitcode 0 успешно
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

# @description Проверить запущена ли служба
# @arg $1 string Имя службы
# @arg $2 string Имя пользователя, необязательный аргумент - если не задано, то действие для системной службы - если задано, то действие для пользовательской службы
# @exitcode 0 служба запущена
# @exitcode 1 нет
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

# @description Добавить службу в автозапуск (при старте ОС) и запустить
# @arg $1 string Имя службы
# @arg $2 string Имя пользователя, необязательный аргумент - если не задано, то действие для системной службы - если задано, то действие для пользовательской службы
# @exitcode 0 успешно
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

# @description Остановить службу и убрать её из автозапуска (при старте ОС)
# @arg $1 string Имя службы
# @arg $2 string Имя пользователя, необязательный аргумент - если не задано, то действие для системной службы - если задано, то действие для пользовательской службы
# @exitcode 0 успешно
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