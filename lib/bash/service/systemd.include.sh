#!/bin/bash

## @brief Функции работы с systemd
## https://systemd.io/
## https://man7.org/linux/man-pages/man1/init.1.html


## @brief Получить путь до директории размещения скриптов запуска системных служб
## @return Путь до директории размещения скриптов запуска системных служб
## @retval 0 - успешно
function systemd_get_system_service_base_dir_path() {
    echo "${GLOBAL_CONFIG_ETC_DIR_PATH}/systemd/system"
    return 0
}

## @brief Получить путь до директории размещения скриптов запуска пользовательских служб
## @param [in] Имя пользователя, необязательный аргумент (если не задано, будет подставлено имя текущего пользователя)
## @return Путь до директории размещения скриптов запуска пользовательских служб
## @retval 0 - успешно
function systemd_get_user_service_base_dir_path() {
    local USER_NAME="${1}"

    local USER_HOME_DIR_PATH=""
    USER_HOME_DIR_PATH=$(user_get_home_dir_path "${USER_NAME}") || return $?
    echo "${USER_HOME_DIR_PATH}/.config/systemd/user"
    return 0
}

## @brief Инициализировать systemd
## @retval 0 - успешно
function systemd_setup() {
    return 0
}

## @brief Проверить запущена ли служба
## @param [in] Имя службы
## @param [in] Имя пользователя, необязательный аргумент
##             - если не задано, то действие для системной службы
##             - если задано, то действие для пользовательской службы
## @retval 0 - служба запущена; 1 - нет
function systemd_service_is_active() {
    local SERVICE_NAME="${1}"
    local USER_NAME="${2}"

    local SERVICE_STATUS=""
    if [[ -z "${USER_NAME}" ]]; then
        SERVICE_STATUS=$(systemctl is-active "${SERVICE_NAME}" 2> "/dev/null") || return $?
    else
        # https://unix.stackexchange.com/a/685029
        # https://www.opennet.ru/opennews/art.shtml?num=54871
        # Опция --machine доступна начиная с 248 версии systemd. Сделан fallback на systemd-run
        # https://manpages.debian.org/testing/systemd/systemd-run.1.en.html
        SERVICE_STATUS=$(systemctl --machine="${USER_NAME}@" --user is-active "${SERVICE_NAME}" 2> "/dev/null") ||
            SERVICE_STATUS=$(systemd-run --machine="${USER_NAME}@" --user --pipe systemctl --user is-active "${SERVICE_NAME}" 2> "/dev/null") || return $?
    fi

    if [[ "${SERVICE_STATUS,,}" == "active" ]]; then
        return 0
    fi
    return 1
}

## @brief Добавить службу в автозапуск (при старте ОС) и запустить
## @param [in] Имя службы
## @param [in] Имя пользователя, необязательный аргумент
##             - если не задано, то действие для системной службы
##             - если задано, то действие для пользовательской службы
## @retval 0 - успешно
function systemd_service_enable() {
    local SERVICE_NAME="${1}"
    local USER_NAME="${2}"

    if [[ -z "${USER_NAME}" ]]; then
        systemctl enable "${SERVICE_NAME}" > "/dev/null" || return $?
        systemctl start "${SERVICE_NAME}" > "/dev/null" || return $?
    else
        systemctl --machine="${USER_NAME}@" --user enable "${SERVICE_NAME}" > "/dev/null" ||
            systemd-run --machine="${USER_NAME}@" --user --pipe systemctl enable "${SERVICE_NAME}" > "/dev/null" || return $?
        systemctl --machine="${USER_NAME}@" --user start "${SERVICE_NAME}" > "/dev/null" ||
            systemd-run --machine="${USER_NAME}@" --user --pipe systemctl start "${SERVICE_NAME}" > "/dev/null" || return $?
    fi
    return 0
}

## @brief Остановить службу и убрать её из автозапуска (при старте ОС)
## @param [in] Имя службы
## @param [in] Имя пользователя, необязательный аргумент
##             - если не задано, то действие для системной службы
##             - если задано, то действие для пользовательской службы
## @retval 0 - успешно
function systemd_service_disable() {
    local SERVICE_NAME="${1}"
    local USER_NAME="${2}"

    if [[ -z "${USER_NAME}" ]]; then
        systemctl stop "${SERVICE_NAME}" > "/dev/null" || return $?
        systemctl disable "${SERVICE_NAME}" > "/dev/null" || return $?
    else
        systemctl --machine="${USER_NAME}@" --user stop "${SERVICE_NAME}" > "/dev/null" ||
            systemd-run --machine="${USER_NAME}@" --user --pipe systemctl stop "${SERVICE_NAME}" > "/dev/null" || return $?
        systemctl --machine="${USER_NAME}@" --user disable "${SERVICE_NAME}" > "/dev/null" ||
            systemd-run --machine="${USER_NAME}@" --user --pipe systemctl disable "${SERVICE_NAME}" > "/dev/null" || return $?
    fi
    return 0
}