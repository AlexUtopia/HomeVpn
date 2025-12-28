#!/bin/bash

## @brief Функции работы с smd сервером
## https://www.samba.org/
## https://wiki.archlinux.org/title/Samba_(%D0%A0%D1%83%D1%81%D1%81%D0%BA%D0%B8%D0%B9)


## @brief Установить пакет SMB сервера
## @retval 0 - успешно
function smb_server_packages_setup() {
    if is_msys; then
        return 0
    fi

    package_manager_install_packages "samba" || return $?
    return 0
}

## @brief Получить путь до файла конфигурации smb сервера
## @return Путь до файла конфигурации smb сервера
## @retval 0 - успешно
function smb_server_get_config_file_path() {
    local SMB_SERVER_BUILD_OPTIONS=""
    SMB_SERVER_BUILD_OPTIONS=$(smbd -b) || return $?

    local REGEX=""
    REGEX=$(printf "CONFIGFILE:[[:blank:]]+([[:graph:]]+)") || return $?

    if [[ "${SMB_SERVER_BUILD_OPTIONS}" =~ ${REGEX} ]]; then
        echo "${BASH_REMATCH[1]}"
        return 0
    fi

    return 1
}

## @brief Создать публичную (общедоступную) директорию
## @retval 0 - успешно
function smb_server_make_public_dir() {
    fs_make_dirs "${GLOBAL_CONFIG_SMB_SERVER_PUBLIC_DIR_PATH}" || return $?
    chmod 0777 "${GLOBAL_CONFIG_SMB_SERVER_PUBLIC_DIR_PATH}" || return $?
    return 0
}

## @brief Создать конфиг SMB сервера
## @retval 0 - успешно
function smb_server_make_config() {
    # https://www.samba.org/samba/docs/current/man-html/smb.conf.5.html

    local SMB_SERVER_CONFIG_FILE_PATH=""
    SMB_SERVER_CONFIG_FILE_PATH=$(smb_server_get_config_file_path) || return $?

    # fixme utopia Задать обнаружение NetBios
    # https://www.linux.org.ru/forum/admin/13225419
    # https://en.wikipedia.org/wiki/NetBIOS#NetBIOS_name
    # getprop ro.product.model
    # getprop ro.product.manufacturer

    # https://learn.microsoft.com/en-us/answers/questions/1280211/symbolic-links-created-by-linux-are-not-displayed
    # fixme utopia Переписать?
    # https://www.samba.org/samba/docs/using_samba/ch08.html#samba2-CHP-8-TABLE-2
    fs_create_file "[global]
workgroup = WORKGROUP
security = user
map to guest = bad user
wins support = no
dns proxy = no
smb ports = ${GLOBAL_CONFIG_SMB_SERVER_TCP_PORTS}
inherit permissions = yes
follow symlinks = yes
wide links = yes
allow insecure wide links = yes

[public]
path = \"${GLOBAL_CONFIG_SMB_SERVER_PUBLIC_DIR_PATH}\"
guest ok = yes
force user = ${GLOBAL_CONFIG_SMB_SERVER_USER}
browsable = yes
writable = yes
" "${SMB_SERVER_CONFIG_FILE_PATH}" || return $?
    return 0
}

# fixme utopia Дописать для windows https://stackoverflow.com/questions/1537065/how-can-i-create-a-shared-folder-from-the-windows-command-line
# https://habr.com/ru/companies/varonis/articles/281691/
# https://stackoverflow.com/a/9422811
# https://stackoverflow.com/questions/5944180/how-do-you-run-a-command-as-an-administrator-from-the-windows-command-line
# https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/manage/understand-special-identities-groups
# https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/manage/understand-special-identities-groups#everyone
# https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2012-r2-and-2012/hh750728(v=ws.11)
# https://stackoverflow.com/questions/5944180/how-do-you-run-a-command-as-an-administrator-from-the-windows-command-line
function windows_net_share_setup() {
    # Название группы Everyone необходимо уточнять через её SID (S-1-1-0), "Все" - это локализованное имя
    # whoami /groups
    # https://learn.microsoft.com/ru-ru/windows/win32/com/runas

    # runas /user:"Администратор" "net share public=\"${GLOBAL_CONFIG_SMB_SERVER_PUBLIC_DIR_PATH}\" /GRANT:Все,FULL" || return $?
    return 0
}

## @brief Настроить Android/termux специфику SMB сервера
## @details https://smarden.org/runit/runscripts#samba
## @param [in] Имя службы
## @retval 0 - успешно
function termux_smb_server_setup() {
    local SMB_SERVER="${1}"

    local SMB_SERVER_EXECUTABLE_PATH=""
    SMB_SERVER_EXECUTABLE_PATH=$(get_executable_path "${SMB_SERVER}") || return $?

    runit_create_run_file "${SMB_SERVER}" \
"#!${SHELL}
exec ${SMB_SERVER_EXECUTABLE_PATH} --foreground --no-process-group --debug-stdout --debuglevel=3 2>&1 || exit \$?
exit 0" || return $?

    termux_set_symlinks_to_storage "${GLOBAL_CONFIG_SMB_SERVER_PUBLIC_DIR_PATH}"
    return 0
}

## @brief Установить и настроить SMB сервер
## @retval 0 - успешно
function smb_server_setup() {
    smb_server_packages_setup || return $?

    if is_msys; then
        windows_net_share_setup || return $?
        return 0
    fi

    # https://ubuntu.com/tutorials/install-and-configure-samba#1-overview
    local SMB_SERVER="smbd"

    service_disable "${SMB_SERVER}"

    smb_server_make_public_dir || return $?
    smb_server_make_config || return $?

    if is_termux; then
        termux_smb_server_setup "${SMB_SERVER}" || return $?
    fi

    service_enable "${SMB_SERVER}" || return $?

    if ! service_is_active "${SMB_SERVER}"; then
        echo "FATAL: ${SMB_SERVER} not started"
        return 1
    fi

    # https://www.samba.org/~tpot/articles/firewall.html
    # https://ixnfo.com/iptables-pravila-dlya-samba.html
    # https://unlix.ru/%D0%BD%D0%B0%D1%81%D1%82%D1%80%D0%BE%D0%B9%D0%BA%D0%B0-%D1%84%D0%B0%D0%B5%D1%80%D0%B2%D0%BE%D0%BB%D0%B0-iptables-%D0%B4%D0%BB%D1%8F-samba/
    # https://entnet.ru/server/domain/ustanovka-i-nastrojka-samba-server.html
    return 0
}