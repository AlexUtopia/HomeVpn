#!/bin/bash

## @brief Функции по установке и работе с waydroid
## https://repo.waydro.id/


# Чтобы waydroid не спрашивал разрешения на подключение adb, прописать в конфиге
# /var/lib/waydroid/waydroid.cfg
# auto_adb = True

# Пробросить kvm в lxc контейнер
# Дать возможность запускать вирт машину обычному пользователю
# sudo usermod -aG libvirt,kvm $USER
# lxc config device add <container_name> kvm unix-char path=/dev/kvm
# https://www.google.com/search?q=lxc+container+pass+kvm+device&sca_esv=9fcb0994feb150f1&biw=1242&bih=554&sxsrf=ANbL-n5olTSR0QXZpwIIiQyG1uQaMWVMYw%3A1771715438966&ei=bjuaabjUOpq_wPAP97CLyAQ&oq=lxc+&gs_lp=Egxnd3Mtd2l6LXNlcnAiBGx4YyAqAggAMgQQIxgnMgQQIxgnMgQQIxgnMgUQABiABDIKEAAYgAQYigUYQzIFEAAYgAQyBRAAGIAEMgUQABiABDIFEAAYgAQyBRAAGIAESOWe7QJQgY7tAlj0lO0CcAZ4AJABAJgBW6AB2wKqAQE0uAEDyAEA-AEBmAIKoAKZBMICBxAAGB4YsAPCAggQABjvBRiwA8ICCxAAGIAEGLEDGIMBwgIREC4YgAQYsQMYgwEYxwEY0QPCAggQABiABBixA8ICBRAuGIAEmAMAiAYBkAYGkgcDNi40oAfDJrIHAzAuNLgH2QPCBwkwLjEuMS41LjPIB6ABgAgB&sclient=gws-wiz-serp



## @brief Установить пакет waydroid
## @details https://docs.waydro.id/usage/install-on-desktops#ubuntu-debian-and-derivatives
## @details https://learn.microsoft.com/en-us/windows/android/wsa/
## @retval 0 - успешно
function waydroid_packages_setup() {
    if package_manager_is_apt; then
        local OS_DISTRO_VERSION_CODENAME=""
        OS_DISTRO_VERSION_CODENAME=$(get_linux_distro_codename_or_version) || return $?

        local PACKAGE_NAME="waydroid"
        local KEY_FILE_URL="https://repo.waydro.id/waydroid.gpg"
        local URIS="https://repo.waydro.id"
        local SUITES="${OS_DISTRO_VERSION_CODENAME}"
        local COMPONENTS="main"
        apt_add_sources "${PACKAGE_NAME}" "${KEY_FILE_URL}" "${URIS}" "${SUITES}" "${COMPONENTS}" || return $?
        package_manager_install_packages "${PACKAGE_NAME}" || return $?
        echo "PACKAGE INSTALLED: \"${PACKAGE_NAME}\", run ${PACKAGE_NAME}"
        return 0
    fi
    return 1
}

## @brief Установить и настроить waydroid
## @retval 0 - успешно
function waydroid_setup() {
    if ! is_linux; then
        return 0
    fi

    waydroid_packages_setup || return $?
    waydroid init || return $?
    service_enable "waydroid-container.service" || return $?
    return 0
}

## @brief Попытаться запустить waydroid сессию
## @details waydroid сессия требует запуска с рамках wayland сессии,
##          которая может отсутствовать на X11 системах. В таком случае функция вернёт ошибку
## @retval 0 - успешно
function waydroid_session_try_start() {
    waydroid session stop || return $?
    waydroid show-full-ui || return $? # Будет запущена сессия waydroid (waydroid session start)
    return 0
}

## @brief Запустить waydroid сессию
## @details waydroid сессия требует запуска с рамках wayland сессии,
##          которая может отсутствовать на X11 системах.
##          В таком случае wayland сессия будет запущена через weston
## @retval 0 - успешно
function waydroid_session_start() {
    echo "[waydroid] Session start 1"
    if waydroid_session_try_start; then
        return 0;
    fi

    weston &
    job_setup_kill_handler "weston"
    sleep 3

    echo "[waydroid] Session start 2"
    export WAYLAND_DISPLAY="wayland-0"
    waydroid_session_try_start || return $?
    return 0
}

## @brief Ожидать запуска waydroid ОС
## @details Максимальное время ожидания 30 секунд
## @details FIFO в качестве временного файла не подходит,
##          т.к. операции чтения/записи для FIFO работают в строго блокирующем режиме
##          что приводит к необходимости запуска отдельного job'а который будет читать FIFO
##          вплоть до завершения job'а waydroid_session_start().
##          Читатель FIFO необходим, т.к. писатель FIFO может быть приостановлен ОС при заполнении FIFO "под завязку"
## @param [in] Путь до временного файла куда перенаправляется stdout/stderr от waydroid сессии
## @retval 0 - успешно
function waydroid_wait_start() {
    local TEMP_FILE_PATH="${1}"
    local TOTAl_TIMEOUT_SEC=30

    # Ждём запуска waydroid UI анализируя stdout/stderr 'wayland session start'
    local START_TIME_POINT=${SECONDS}
    while (( (SECONDS - START_TIME_POINT) < TOTAl_TIMEOUT_SEC )); do
        if ! IFS= read -t 1 -r LINE; then
            sleep 1
            continue
        fi

        echo "${LINE}"
        REGEX="Android with user [0-9]+ is ready"
        if [[ "${LINE}" =~ ${REGEX} ]]; then
            echo "[waydroid] Started OK"
            sleep 3
            return 0
        fi
    done < "${TEMP_FILE_PATH}"
    echo "[waydroid] Started FAIL"
    return 1
}

## @brief Установить termux в waydroid
## @details Путь до termux apk берётся из вызова функции termux_get_apk_path()
## @retval 0 - успешно
function waydroid_termux_install() {
    local TERMUX_APK_PATH=""
    TERMUX_APK_PATH=$(termux_get_apk_path) || return $?
    waydroid app install "${TERMUX_APK_PATH}" || return $?
    return 0
}

## @brief Установить для ssh сервера в termux ключ для подключения ssh клиента (текущий хост)
## @details Если текущий хост не имеет ssh ключа (публичный/приватный),
##          ключ будет сгенерирован автоматически (без запросов пользователю)
## @details Текущий публичный ключ хоста копируется в файл (директория .ssh уже должна существовать)
##          ~/.local/share/waydroid/data/data/com.termux/files/home/.ssh/authorized_keys
## @retval 0 - успешно
function waydroid_termux_setup_ssh_server_authorized_keys() {
    local USER_HOME_DIR_PATH=""
    USER_HOME_DIR_PATH="$(user_get_logname_home_dir_path)" || return $?

    local SSH_PRIVATE_KEY_FILE_PATH=""
    SSH_PRIVATE_KEY_FILE_PATH=$(ssh_client_get_private_key_file_path_for_logname_user) || return $?
    local SSH_PUBLIC_KEY_FILE_PATH="${SSH_PRIVATE_KEY_FILE_PATH}.pub"

    local WAYDROID_TERMUX_SSH_AUTHORIZED_KEYS_FILE_PATH="${USER_HOME_DIR_PATH}/.local/share/waydroid/data/data/${TERMUX_PACKAGE_NAME}/files/home/.ssh/authorized_keys"

    sudo cp --force "${SSH_PUBLIC_KEY_FILE_PATH}" "${WAYDROID_TERMUX_SSH_AUTHORIZED_KEYS_FILE_PATH}" || return $?
    return 0
}

## @brief Установить все требуемые разрешения для termux
## @details Узнать разрешения запрашиваемые приложением можно так:
##          sudo waydroid shell -- bash -c "dumpsys package com.termux"
##
##          См. секцию "runtime permissions"
## @retval 0 - успешно
function waydroid_termux_setup_permissions() {
    sudo waydroid shell -- bash -c \
    "pm grant ${TERMUX_PACKAGE_NAME} android.permission.POST_NOTIFICATIONS && \
pm grant ${TERMUX_PACKAGE_NAME} android.permission.READ_EXTERNAL_STORAGE && \
pm grant ${TERMUX_PACKAGE_NAME} android.permission.READ_MEDIA_IMAGES && \
pm grant ${TERMUX_PACKAGE_NAME} android.permission.READ_MEDIA_AUDIO && \
pm grant ${TERMUX_PACKAGE_NAME} android.permission.READ_MEDIA_VIDEO && \
pm grant ${TERMUX_PACKAGE_NAME} android.permission.WRITE_EXTERNAL_STORAGE && \
pm grant ${TERMUX_PACKAGE_NAME} android.permission.ACCESS_MEDIA_LOCATION" || return $?
    return 0
}

## @brief Запустить termux
## @details Функция учитывает необходимые задержки до и после запуска termux
## @retval 0 - успешно
function waydroid_termux_run() {
    sleep 3
    waydroid app launch "${TERMUX_PACKAGE_NAME}" || return $?
    sleep 3
    return 0
}

## @brief Запустить ssh сервер в termux
## @details Запуск осуществляется при помощи ввода текста средствами отладки Android.
##          При этом обратной связи от termux мы не имеем
## @details ssh сервер (sshd) упредительно устанавливается если нужно (пакет openssh)
## @retval 0 - успешно
function waydroid_termux_run_ssh_server() {
    local ENTER_KEY_EVENT_CODE=66
    sudo waydroid shell -- bash -c "input text \"apt update && apt install -y openssh && sshd\" && input keyevent ${ENTER_KEY_EVENT_CODE}" || return $?
    return 0
}

## @brief Подготовить termux для удалённого к нему подключения по ssh
## @retval 0 - успешно
function waydroid_termux_setup() {
    waydroid_termux_install || return $?
    waydroid_termux_setup_ssh_server_authorized_keys || return $?
    waydroid_termux_setup_permissions || return $?
    waydroid_termux_run || return $?
    waydroid_termux_run_ssh_server || return $?
    return 0
}

## @brief Получить IP адрес waydroid
## @return IP адрес waydroid
## @retval 0 - успешно
function waydroid_get_ip_address() {
    local WAYDROID_STATUS=""
    WAYDROID_STATUS=$(waydroid status) || return $?

    local REGEX=""
    REGEX=$(printf "IP address:[[:blank:]]+([[:graph:]]+)") || return $?

    if [[ "${WAYDROID_STATUS}" =~ ${REGEX} ]]; then
        echo "${BASH_REMATCH[1]}"
        return 0
    fi
    return 1
}

## @brief Попытаться выполнить удалённую команду по ssh в termux (bash)
## @details Подключение не требуется ввода пароля. Подключение осуществляется с помощью ключей.
##          См. функцию waydroid_termux_setup_ssh_server_authorized_keys()
## @param [in] ... Команда на исполнение в termux (bash)
## @retval 0 - успешно;
##         255 - специальный код ошибки обозначающий что соединение с ssh сервером установить не удалось;
##         прочие коды ошибок - результат выполнения удалённой команды в termux (bash)
function waydroid_termux_shell_try_run_command_over_ssh() {
    local USER_NAME=""
    USER_NAME=$(user_get_logname) || return $?

    local SSH_PRIVATE_KEY_FILE_PATH=""
    SSH_PRIVATE_KEY_FILE_PATH=$(ssh_client_get_private_key_file_path_for_logname_user) || return $?

    local WAYDROID_IP_ADDRESS=""
    WAYDROID_IP_ADDRESS=$(waydroid_get_ip_address) || return ${SSH_CLIENT_CONNECTION_ERROR_CODE}

    sudo --user="${USER_NAME}" ssh -i "${SSH_PRIVATE_KEY_FILE_PATH}" -p 8022 "${WAYDROID_IP_ADDRESS}" "bash -c '$*'" || return $?
    return 0
}

## @brief Выполнить удалённую команду по ssh в termux (bash)
## @details Подключение не требуется ввода пароля. Подключение осуществляется с помощью ключей.
##          См. функцию waydroid_termux_setup_ssh_server_authorized_keys()
## @details Максимальное время ожидания подключения по ssh - 40 секунд
## @param [in] ... Команда на исполнение в termux (bash)
## @retval 0 - успешно;
##         255 - специальный код ошибки обозначающий что соединение с ssh сервером установить не удалось;
##         прочие коды ошибок - результат выполнения удалённой команды в termux (bash)
function waydroid_termux_shell_run_command_over_ssh() {
    local TOTAl_TIMEOUT_SEC=40

    local SSH_CLIENT_ERROR_CODE=1
    local START_TIME_POINT=${SECONDS}
    while (( (SECONDS - START_TIME_POINT) < TOTAl_TIMEOUT_SEC )); do
        waydroid_termux_shell_try_run_command_over_ssh "$*"

        # 255 - специальный код ошибки обозначающий что соединение с ssh сервером установить не удалось
        # Все прочие коды ошибок - результат выполнения удалённой команды
        SSH_CLIENT_ERROR_CODE=$?
        if (( SSH_CLIENT_ERROR_CODE == SSH_CLIENT_CONNECTION_ERROR_CODE )); then
            sleep 1
            continue
        fi
        return ${SSH_CLIENT_ERROR_CODE}
    done
    return ${SSH_CLIENT_ERROR_CODE}
}

## @brief Выполнить команду в termux (bash)
## @param [in] ... Команда на исполнение в termux (bash)
## @retval 0 - успешно;
##         255 - специальный код ошибки обозначающий что соединение с ssh сервером установить не удалось;
##         прочие коды ошибок - результат выполнения удалённой команды в termux (bash)
function waydroid_termux_shell_run_command() {
    local TEMP_FILE_PATH=""
    TEMP_FILE_PATH=$(mktemp) &&
    trap_add_remove_temp_path_handler "${TEMP_FILE_PATH}" || return $?

    waydroid_session_start &> "${TEMP_FILE_PATH}" &
    job_setup_kill_handler "waydroid_session_start" "waydroid session stop"

    waydroid_wait_start "${TEMP_FILE_PATH}" || return $?

    waydroid_termux_setup || return $?
    waydroid_termux_shell_run_command_over_ssh "$*" || return $?
    return 0
}
