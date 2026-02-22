#!/bin/bash

# Скачать adb отдельно
# https://developer.android.com/tools/releases/platform-tools?hl=ru

# https://docs.waydro.id/usage/install-on-desktops

#set -x

# настроить запуск службы systemd
# https://www.google.com/search?q=waydroid-container.service+vs+waydroid+session+start&sca_esv=45931f64f015fd65&sxsrf=ANbL-n6ES3rOiBpNUrjel4_duXgzRxRFXA%3A1771719610881&ei=ukuaad_ANZC2wPAPsYbXoQc&biw=1242&bih=554&ved=0ahUKEwjfhbHw6euSAxUQGxAIHTHDNXQQ4dUDCBE&uact=5&oq=waydroid-container.service+vs+waydroid+session+start&gs_lp=Egxnd3Mtd2l6LXNlcnAiNHdheWRyb2lkLWNvbnRhaW5lci5zZXJ2aWNlIHZzIHdheWRyb2lkIHNlc3Npb24gc3RhcnQyCBAAGIAEGKIEMggQABiABBiiBDIFEAAY7wUyBRAAGO8FMgUQABjvBUjCuQRQAFjNtQRwAngBkAEAmAGEAaABqxqqAQUyNC4xMrgBA8gBAPgBAvgBAZgCJqACpB3CAgQQABgewgIGEAAYCBgewgIFECEYoAHCAgcQIRgKGKABwgIFECEYnwXCAgQQIRgVmAMAkgcFMTcuMjGgB5djsgcFMTUuMjG4B5sdwgcLMC4xMS4xOC44LjHIB90BgAgB&sclient=gws-wiz-serp

# /var/lib/waydroid/waydroid.cfg
# auto_adb = True

# Скачать termux
# https://f-droid.org/repo/com.termux_1022.apk

# Установить termux
# waydroid app install ~/Загрузки/com.termux_1022.apk

# Дать разрешения для termux (выдать сразу все)
# sudo waydroid shell "pm grant com.termux android.permission.POST_NOTIFICATIONS"

# сгенерировать ssh ключ

# передать публичный ssh ключ сюда (скопировать + переименовать)
# ~/.local/share/waydroid/data/data/com.termux/files/home/.ssh/authorized_keys

# Запустить termux
# waydroid app launch com.termux


# при помощи команд (sudo waydroid shell)
# input text "xxx"
# input keyevent <код клавиши>
# активировать sshd
# sudo waydroid shell -- bash -c "input text \"apt update && apt install -y openssh && sshd\" && input keyevent 66"

# Узнать IP адрес для подключения
# waydroid status
#    Session:	RUNNING
#    Container:	RUNNING
#    Vendor type:	MAINLINE
#    IP address:	192.168.240.112
#    Session user:	utopia(1000)
#    Wayland display:	wayland-0

# Подключиться по ssh к termux (подождать и в цикле пытаться подключиться - 2 попытки)
# ssh -p 8022 192.168.240.112

# Пробросить kvm в lxc контейнер
#   Дать возможность запускать вирт машину обычному пользователю
#   sudo usermod -aG libvirt,kvm $USER
#   lxc config device add <container_name> kvm unix-char path=/dev/kvm
#   https://www.google.com/search?q=lxc+container+pass+kvm+device&sca_esv=9fcb0994feb150f1&biw=1242&bih=554&sxsrf=ANbL-n5olTSR0QXZpwIIiQyG1uQaMWVMYw%3A1771715438966&ei=bjuaabjUOpq_wPAP97CLyAQ&oq=lxc+&gs_lp=Egxnd3Mtd2l6LXNlcnAiBGx4YyAqAggAMgQQIxgnMgQQIxgnMgQQIxgnMgUQABiABDIKEAAYgAQYigUYQzIFEAAYgAQyBRAAGIAEMgUQABiABDIFEAAYgAQyBRAAGIAESOWe7QJQgY7tAlj0lO0CcAZ4AJABAJgBW6AB2wKqAQE0uAEDyAEA-AEBmAIKoAKZBMICBxAAGB4YsAPCAggQABjvBRiwA8ICCxAAGIAEGLEDGIMBwgIREC4YgAQYsQMYgwEYxwEY0QPCAggQABiABBixA8ICBRAuGIAEmAMAiAYBkAYGkgcDNi40oAfDJrIHAzAuNLgH2QPCBwkwLjEuMS41LjPIB6ABgAgB&sclient=gws-wiz-serp

# Убрать фоновые процессы
# https://www.google.com/search?q=bash+script+background+process+kill&sca_esv=9fcb0994feb150f1&biw=1242&bih=554&sxsrf=ANbL-n4spcaHeoQiMJ24yp_I4PtKZLt9Gw%3A1771722634496&ei=ileaaYD-HbnLwPAPqby6eA&ved=0ahUKEwiA65OS9euSAxW5JRAIHSmeDg8Q4dUDCBE&uact=5&oq=bash+script+background+process+kill&gs_lp=Egxnd3Mtd2l6LXNlcnAiI2Jhc2ggc2NyaXB0IGJhY2tncm91bmQgcHJvY2VzcyBraWxsMgYQABgWGB4yCBAAGIAEGKIEMggQABiABBiiBDIFEAAY7wUyBRAAGO8FSNhFUPsgWMdCcAJ4AZABAJgBVaAB6geqAQIxM7gBA8gBAPgBAZgCD6ACvwnCAgoQABhHGNYEGLADwgIHECMYsAIYJ8ICBhAAGAcYHsICCBAAGAcYHhgTwgIIEAAYgAQYywGYAwCIBgGQBgiSBwQxMi4zoAfJUbIHBDEwLjO4B6MJwgcHMi01LjguMsgHpQGACAE&sclient=gws-wiz-serp

TERMUX_PACKAGE_NAME="com.termux"

function waydroid_jobs_cleanup() {
    local FINALLY_ACTION="${1}"

    echo "[${FINALLY_ACTION}]"
    echo "$(jobs)"

    kill -- -$$ || return $?
    return 0
}


function waydroid_start_base() {
    waydroid session stop || return $?
    waydroid show-full-ui || return $? # Будет запущена сессия waydroid (waydroid session start)
    return 0
}

function waydroid_start() {
    if waydroid_start_base; then
        return 0;
    fi

    weston || return $? &
    sleep 3

    export WAYLAND_DISPLAY=wayland-0
    waydroid_start_base || return $?
    return 0
}

function waydroid_get_termux_apk_path() {
    echo "${GLOBAL_CONFIG_OPT_DIR_PATH}/termux/${TERMUX_PACKAGE_NAME}.apk"
    return 0
}

function waydroid_install_termux() {
    local DOWNLOAD_URL="https://f-droid.org/repo/${TERMUX_PACKAGE_NAME}_1022.apk"
    local INSTALL_PATH=""
    INSTALL_PATH="$(waydroid_get_termux_apk_path)" || return $?

    download "${DOWNLOAD_URL}" "${INSTALL_PATH}" "remake_dirs" || return $?

    waydroid app install "${INSTALL_PATH}" || return $?
    return 0
}

# runtime permissions:
  #        android.permission.POST_NOTIFICATIONS: granted=true, flags=[ USER_SET|USER_SENSITIVE_WHEN_GRANTED|USER_SENSITIVE_WHEN_DENIED]
  #        android.permission.READ_EXTERNAL_STORAGE: granted=true, flags=[ USER_SET|REVOKE_WHEN_REQUESTED|USER_SENSITIVE_WHEN_GRANTED|USER_SENSITIVE_WHEN_DENIED|RESTRICTION_INSTALLER_EXEMPT]
  #        android.permission.READ_MEDIA_IMAGES: granted=true, flags=[ USER_SET|REVOKE_WHEN_REQUESTED|USER_SENSITIVE_WHEN_GRANTED|USER_SENSITIVE_WHEN_DENIED]
  #        android.permission.READ_MEDIA_AUDIO: granted=true, flags=[ USER_SET|REVOKE_WHEN_REQUESTED|USER_SENSITIVE_WHEN_GRANTED|USER_SENSITIVE_WHEN_DENIED]
  #        android.permission.READ_MEDIA_VIDEO: granted=true, flags=[ USER_SET|REVOKE_WHEN_REQUESTED|USER_SENSITIVE_WHEN_GRANTED|USER_SENSITIVE_WHEN_DENIED]
  #        android.permission.WRITE_EXTERNAL_STORAGE: granted=true, flags=[ USER_SET|USER_SENSITIVE_WHEN_GRANTED|USER_SENSITIVE_WHEN_DENIED|RESTRICTION_INSTALLER_EXEMPT]
  #        android.permission.ACCESS_MEDIA_LOCATION: granted=true, flags=[ USER_SET|REVOKE_WHEN_REQUESTED|USER_SENSITIVE_WHEN_GRANTED|USER_SENSITIVE_WHEN_DENIED]
function waydroid_setup_termux_permissions() {
    sudo waydroid shell -- bash -c "pm grant ${TERMUX_PACKAGE_NAME} android.permission.POST_NOTIFICATIONS" || return $?
    return 0
}

function waydroid_setup_ssh_key() {
    local LOGGED_USER_HOME_DIR_PATH=""
    LOGGED_USER_HOME_DIR_PATH="$(user_get_logged_user_home_dir_path)" || return $?
    local SSH_PRIVATE_KEY_FILE_PATH="${LOGGED_USER_HOME_DIR_PATH}/.ssh/id_rsa"
    local SSH_PUBLIC_KEY_FILE_PATH="${SSH_PRIVATE_KEY_PATH}.pub"
    if ! [[ -e "${SSH_PRIVATE_KEY_FILE_PATH}" ]]; then
        ssh-keygen -q -N "" -f "${SSH_PRIVATE_KEY_FILE_PATH}" || return $?
    fi

    local WAYDROID_TERMUX_SSH_AUTHORIZED_KEYS_FILE_PATH="${LOGGED_USER_HOME_DIR_PATH}/.local/share/waydroid/data/data/${TERMUX_PACKAGE_NAME}/files/home/.ssh/authorized_keys"

    fs_create_symlink "${SSH_PUBLIC_KEY_FILE_PATH}" "${WAYDROID_TERMUX_SSH_AUTHORIZED_KEYS_FILE_PATH}" || return $?
    return 0
}

function waydroid_run_termux() {
    waydroid app launch "${TERMUX_PACKAGE_NAME}" || return $?
    return 0
}

function waydroid_termux_run_sshd() {
    sudo waydroid shell -- bash -c "input text \"apt update && apt install -y openssh && sshd\" && input keyevent 66" || return $?
    return 0
}

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

function waydroid_setup_termux() {
    waydroid_install_termux || return $?
    waydroid_setup_ssh_key || return $?
    waydroid_setup_termux_permissions || return $?
    waydroid_run_termux || return $?
    waydroid_termux_run_sshd || return $?
    return 0
}

function waydroid_termux_shell_over_ssh() {
    local WAYDROID_IP_ADDRESS=""
    WAYDROID_IP_ADDRESS=$(waydroid_get_ip_address) || return $?
    ssh -p 8022 ${WAYDROID_IP_ADDRESS} bash -c "$*"
    return 0
}

trap 'waydroid_jobs_cleanup SIGINT' SIGINT
trap 'waydroid_jobs_cleanup EXIT' EXIT

waydroid_start || exit $?
exit 0