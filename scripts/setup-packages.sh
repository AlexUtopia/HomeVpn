#!/bin/bash

# Понять что мы исполняемся внутри вирт машины
# https://unix.stackexchange.com/questions/89714/easy-way-to-determine-the-virtualization-technology-of-a-linux-machine

# Узнать зависимости pip пакетов
# https://stackoverflow.com/a/67111193

# fixme utopia VNC сервер для Windows (для tigervnc пишут что сервер не поддерживается)
# fixme utopia RDP сервер для Linux / Android/termux
# fixme utopia Установка дополнений гостевой ОС?? требуется ли
# fixme utopia Настройка nmbd
# fixme utopia gvfs для Android/termux
# fixme utopia Инструкция по scp
# fixme utopia [Windows/MSYS2] Настройка шареной папки + настройка RDP сервера (RDPWrapper)
# fixme utopia Делать ли upgrade pip? И как его правильно делать? https://stackoverflow.com/a/8550546

# fixme utopia Настройка микрофона в браузере
# Звук с микрофона использовать для браузера, например (не забыть выдать разрешение на микрофон для Termux:API, проверть точно ли нужно это разрешение)
# $PREFIX/etc/pulse/default.pa
# load-module module-sles-source
# https://github.com/termux/termux-app/issues/1448
# https://www.reddit.com/r/termux/comments/icp29x/help_using_pulseaudio_on_termux/

# https://unix.stackexchange.com/a/306115


set -x # Раскомментировать для отладки

HOME_VPN_PROJECT_ROOT="$(dirname "$(readlink -f "${0}")")/.."

source "${HOME_VPN_PROJECT_ROOT}/lib/bash/os.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/config.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/bash.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/fs.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/user.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/git.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/download.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/termux.include.sh"

source "${HOME_VPN_PROJECT_ROOT}/lib/bash/package_manager.include.sh"

source "${HOME_VPN_PROJECT_ROOT}/lib/bash/service.include.sh"

source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/python.include.sh"

source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/cpuid.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/dev_packages.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/dns_dhcp_server.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/firewall.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/make.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/network.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/openjdk.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/openvpn.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/openvpn3.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/pci.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/pycharm.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/qemu.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/rdp_client.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/smb_server.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/ssh_client.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/ssh_server.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/startup.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/telnet_client.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/vnc_client.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/vnc_server.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/waidroid.include.sh"
source "${HOME_VPN_PROJECT_ROOT}/lib/bash/packages/wine.include.sh"


### Full packages begin

DOUBLE_COMMANDER_PACKAGE="doublecmd-qt"
if is_termux; then
    DOUBLE_COMMANDER_PACKAGE=""
elif is_msys; then
    DOUBLE_COMMANDER_PACKAGE="" # Скачаем и установим приложение вручную
fi

MIDNIGHT_COMMANDER_PACKAGE="mc"

FIREFOX_PACKAGE="firefox"
if is_msys; then
    FIREFOX_PACKAGE="" # Скачаем и установим приложение вручную
fi

QT_CREATOR_PACKAGE="qtcreator"
if is_termux; then
    QT_CREATOR_PACKAGE="qt-creator"
elif is_msys; then
    QT_CREATOR_PACKAGE="${GLOBAL_CONFIG_MSYS2_PACKAGE_PREFIX}qt-creator"
fi

LIBREOFFICE_PACKAGE="libreoffice"
if is_termux; then
    LIBREOFFICE_PACKAGE=""
elif is_msys; then
    LIBREOFFICE_PACKAGE="" # Скачаем и установим приложение вручную
fi

TRANSMISSION_PACKAGE="transmission"
if is_msys; then
    TRANSMISSION_PACKAGE="${GLOBAL_CONFIG_MSYS2_PACKAGE_PREFIX}transmission-qt"
fi

FULL_PACKAGES="${DOUBLE_COMMANDER_PACKAGE} ${MIDNIGHT_COMMANDER_PACKAGE} ${FIREFOX_PACKAGE} ${QT_CREATOR_PACKAGE} ${LIBREOFFICE_PACKAGE} ${TRANSMISSION_PACKAGE}"
### Full packages end




# https://www.baeldung.com/linux/find-default-sorting-order
# fixme utopia что будет если в результирующем пути встретится пробел?
# https://unix.stackexchange.com/questions/9496/looping-through-files-with-spaces-in-the-names
# https://unix.stackexchange.com/a/200335
# https://www.gnu.org/software/bash/manual/html_node/The-Shopt-Builtin.html
# https://unix.stackexchange.com/questions/34325/sorting-the-output-of-find-print0-by-piping-to-the-sort-command
# https://stackoverflow.com/a/69375372
function get_directory_paths() {
    local -n RESULT_REF=${1}
    local DIR_PATH="${2}"
    local PATH_WILDCARDS="${3}"
    if [[ -z "${PATH_WILDCARDS}" ]]; then
        PATH_WILDCARDS="*"
    fi
    local TYPE="${4}"
    if [[ -z "${TYPE}" ]]; then
        TYPE="f"
    fi
    local MAXDEPTH="${4}"
    local MAXDEPTH_COMMAND_LINE=""
    if [[ -z "${MAXDEPTH}" ]]; then
        MAXDEPTH_COMMAND_LINE=""
    else
        MAXDEPTH_COMMAND_LINE="-maxdepth ${MAXDEPTH}"
    fi

    local NULL_SYMBOL=$'\0'

    while IFS= read -r -d "${NULL_SYMBOL}" FILE_PATH; do
        # echo "${FILE_PATH}" fixme utopia del?
        RESULT_REF+=("${FILE_PATH}")
    done < <(find "${DIR_PATH}" ${MAXDEPTH_COMMAND_LINE} -name "${PATH_WILDCARDS}" -type "${TYPE}" -print0 | sort -z -V)
    return 0
}

function change_rights_on_directory_recursively_or_file() {
    local TARGET_USER="${1}"
    local DIR_OR_FILE_PATH="${2}"
    local TARGET_GROUP="${TARGET_USER}"

    chown -R "${TARGET_USER}:${TARGET_GROUP}" "${DIR_OR_FILE_PATH}" > "/dev/null" || return $?
    return 0
}


### System firewall begin
# https://selectel.ru/blog/setup-iptables-linux/
# https://losst.pro/kak-sohranit-pravila-iptables

function firewall_accept_tcp_traffic_for_port() {
    if [[ -z "${1}" ]]; then
        echo "TCP port not specified"
        return 1
    fi

    iptables -A INPUT -p tcp --dport ${1} -j ACCEPT || return $?
    return 0
}

function firewall_accept_udp_traffic_for_port() {
    if [[ -z "${1}" ]]; then
        echo "UDP port not specified"
        return 1
    fi

    iptables -A INPUT -p udp --dport ${1} -j ACCEPT || return $?
    return 0
}

### System firewall end


function desktop_environment_get_desktop_file_path() {
    local DESKTOP_ENVIRONMENT_PRIORITY_LIST="xfce cinnamon"
    local DESKTOP_ENVIRONMENT_DIR_PATH="${GLOBAL_CONFIG_USR_DIR_PATH}/share/xsessions"

    local DESKTOP_ENVIRONMENT_FILE_PATH_LIST=()
    get_directory_paths DESKTOP_ENVIRONMENT_FILE_PATH_LIST "${DESKTOP_ENVIRONMENT_DIR_PATH}" || return $?

    for ((i=0; i<=${#DESKTOP_ENVIRONMENT_FILE_PATH_LIST[@]}; i++)); do
        DESKTOP_ENVIRONMENT_FILE_PATH="${DESKTOP_ENVIRONMENT_FILE_PATH_LIST[i]}"
        for DESKTOP_ENVIRONMENT in ${DESKTOP_ENVIRONMENT_PRIORITY_LIST}; do
            if [[ "${DESKTOP_ENVIRONMENT_FILE_PATH}" == *"${DESKTOP_ENVIRONMENT}.desktop" ]]; then
               echo "${DESKTOP_ENVIRONMENT_FILE_PATH}"
               return 0
            fi
        done
    done
    return 1
}

function regex_zero_or_one() {
    local PARAM="${1}"

    echo "(?>${PARAM}){0,1}"
    return 0
}

# https://www.gnu.org/software/sed/manual/html_node/Text-search-across-multiple-lines.html
# https://unix.stackexchange.com/questions/251013/bash-regex-capture-group
# https://www.gnu.org/software/bash/manual/bash.html
# https://learnbyexample.github.io/learn_gnugrep_ripgrep/perl-compatible-regular-expressions.html
# https://unix.stackexchange.com/questions/13466/can-grep-output-only-specified-groupings-that-match

# https://www.gnu.org/software/bash/manual/html_node/Bash-Variables.html#index-BASH_005fREMATCH
# https://www.gnu.org/software/bash/manual/html_node/Conditional-Constructs.html
# https://gist.github.com/CMCDragonkai/6c933f4a7d713ef712145c5eb94a1816

# https://learnbyexample.github.io/learn_gnugrep_ripgrep/perl-compatible-regular-expressions.html#string-anchors
function desktop_file_get_value() {
    local DESKTOP_ENTRY_FILE_PATH="${1}"
    local GROUP_NAME="${2}"
    local KEY="${3}"

    # fixme utopia Написать тесты (printf)

    local WHITESPACE_CHARACTER_SET="[ \t]"
    local NEWLINE_CHARACTER_SET="[\n\r]"
    local ONE_OR_MORE_NEW_LINES="${NEWLINE_CHARACTER_SET}+"
    local ZERO_OR_MORE_NEW_LINES="${NEWLINE_CHARACTER_SET}*"
    local ONE_OR_MORE_WHITESPACES="${WHITESPACE_CHARACTER_SET}+"
    local ZERO_OR_MORE_WHITESPACES="${WHITESPACE_CHARACTER_SET}*"

    local GROUP_HEADER="\[${GROUP_NAME}\]${ZERO_OR_MORE_WHITESPACES}"
    local GROUP_HEADER_SEARCH_REGEX="(?>^${GROUP_HEADER}|${NEWLINE_CHARACTER_SET}${GROUP_HEADER})"

    # fixme utopia Вынести в отдельный метод
    # https://unix.stackexchange.com/questions/720268/what-is-modifier-in-locale-name
    # https://www.gnu.org/software/gettext/manual/html_node/Locale-Names.html
    # https://www.gnu.org/software/libc/manual/html_node/Locale-Names.html
    local BASE_KEY_TEMPLATE="[A-Za-z][A-Za-z0-9-]*"
    local LANG_TEMPLATE="${BASE_KEY_TEMPLATE}"
    local COUNTRY_TEMPLATE="_${BASE_KEY_TEMPLATE}"
    local ENCODING_TEMPLATE="\.${BASE_KEY_TEMPLATE}"
    local MODIFIER_TEMPLATE="@${BASE_KEY_TEMPLATE}"
    local KEY_LANG_COUNTRY_MODIFIER=$(regex_zero_or_one "\[${LANG_TEMPLATE}$(regex_zero_or_one "${COUNTRY_TEMPLATE}")$(regex_zero_or_one "${ENCODING_TEMPLATE}")$(regex_zero_or_one "${MODIFIER_TEMPLATE}")\]")
    local KEY_TEMPLATE="${BASE_KEY_TEMPLATE}${KEY_LANG_COUNTRY_MODIFIER}"

    local COMMENT_LINE_TEMPLATE="${ZERO_OR_MORE_WHITESPACES}#.*"

    local KEY_VALUE_TARGET="${KEY}${ZERO_OR_MORE_WHITESPACES}=${ZERO_OR_MORE_WHITESPACES}(.*)"
    local KEY_VALUE_OTHER="${KEY_TEMPLATE}${ZERO_OR_MORE_WHITESPACES}=${ZERO_OR_MORE_WHITESPACES}.*"
    local KEY_VALUE_REGEX="(?>${KEY_VALUE_TARGET}|${KEY_VALUE_OTHER}|${ONE_OR_MORE_WHITESPACES}|${COMMENT_LINE_TEMPLATE}|${ONE_OR_MORE_NEW_LINES})"

    local REGEX="${GROUP_HEADER_SEARCH_REGEX}${KEY_VALUE_REGEX}+"

    local RESULT=""
    RESULT=$(cat "${DESKTOP_ENTRY_FILE_PATH}" | pcregrep --only-matching=1 --multiline "${REGEX}" ) || return $?
    echo "${RESULT}"
    return 0
}

function vnc_server_create_xstartup() {
    local VNC_USER="${1}"
    local XSTARTUP_FILE_PATH="${2}"

    local DESKTOP_ENVIRONMENT_DESKTOP_FILE_PATH=""
    DESKTOP_ENVIRONMENT_DESKTOP_FILE_PATH=$(desktop_environment_get_desktop_file_path) || return $?

    local EXEC=""
    EXEC=$(desktop_file_get_value "${DESKTOP_ENVIRONMENT_DESKTOP_FILE_PATH}" "Desktop Entry" "Exec") || return $?

    fs_create_file "#!${SHELL}
autocutsel -fork
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
${EXEC}" "${XSTARTUP_FILE_PATH}" "${VNC_USER}" || return $?
    fs_set_file_as_executable "${XSTARTUP_FILE_PATH}" || return $?
    return 0
}

function vnc_server_get_executable_path() {
    get_executable_path "vncserver" || return $?
    return 0
}

function vnc_server_get_config_info() {
    local -n RESULT_REF=${1}
    local VNC_USER="${2}"

    local INIT_SYSTEM_BASE_DIR_PATH=""
    local INIT_SYSTEM_CONFIG_SEARCH_DIR_PATH=""
    local INIT_SYSTEM_BASE_DIR_PATH_FILTER_TYPE=""
    local INIT_SYSTEM_CONFIG_SEARCH_DIR_MAXDEPTH=""
    if is_termux; then
        INIT_SYSTEM_BASE_DIR_PATH="$(runit_get_base_dir_path)"
        INIT_SYSTEM_CONFIG_SEARCH_DIR_PATH="${INIT_SYSTEM_BASE_DIR_PATH}"
        INIT_SYSTEM_BASE_DIR_PATH_FILTER_TYPE="d"
        INIT_SYSTEM_CONFIG_SEARCH_DIR_MAXDEPTH=1
    else
        INIT_SYSTEM_BASE_DIR_PATH="$(systemd_get_user_service_base_dir_path "${VNC_USER}")"
        INIT_SYSTEM_CONFIG_SEARCH_DIR_PATH="${GLOBAL_CONFIG_ROOT_PATH}/home"
        INIT_SYSTEM_BASE_DIR_PATH_FILTER_TYPE="f"
    fi

    local VNCD_BASENAME="vncd"
    local VNCD_INSTANCE_NAME_REGEX="${VNCD_BASENAME}@(.+)-([0-9]+).service$"

    local VNC_USER_HOME_DIRECTORY_PATH=""
    VNC_USER_HOME_DIRECTORY_PATH=$(user_get_home_dir_path "${VNC_USER}") || return $?
    local VNC_XSTARTUP_FILE_PATH="${VNC_USER_HOME_DIRECTORY_PATH}/.vnc/xstartup"

    local VNC_SERVER_EXECUTABLE_PATH=""
    VNC_SERVER_EXECUTABLE_PATH=$(vnc_server_get_executable_path) || return $?

    RESULT_REF["EXECUTABLE_PATH"]="${VNC_SERVER_EXECUTABLE_PATH}"
    RESULT_REF["USER"]="${VNC_USER}"
    RESULT_REF["USER_HOME_DIRECTORY_PATH"]="${VNC_USER_HOME_DIRECTORY_PATH}"
    RESULT_REF["XSTARTUP_FILE_PATH"]="${VNC_XSTARTUP_FILE_PATH}"

    local INIT_SYSTEM_CONFIG_PATH_LIST=()
    get_directory_paths INIT_SYSTEM_CONFIG_PATH_LIST "${INIT_SYSTEM_CONFIG_SEARCH_DIR_PATH}" "${VNCD_BASENAME}@*.service" "${INIT_SYSTEM_BASE_DIR_PATH_FILTER_TYPE}" "${INIT_SYSTEM_CONFIG_SEARCH_DIR_MAXDEPTH}" || return $?

    local DISPLAY_NUMBER="0"
    for ((i=0; i<=${#INIT_SYSTEM_CONFIG_PATH_LIST[@]}; i++)); do
        local INIT_SYSTEM_CONFIG_PATH="${INIT_SYSTEM_CONFIG_PATH_LIST[i]}"

        if [[ "${INIT_SYSTEM_CONFIG_PATH}" =~ ${VNCD_INSTANCE_NAME_REGEX} ]]; then
            local VNCD_INSTANCE_NAME="${BASH_REMATCH[0]}"
            local VNCD_INSTANCE_USER="${BASH_REMATCH[1]}"
            local VNCD_INSTANCE_DISPLAY_NUMBER="${BASH_REMATCH[2]}"

            if [[ "${VNCD_INSTANCE_USER}" == "${VNC_USER}" ]]; then
                RESULT_REF["INSTANCE_NAME"]="${VNCD_INSTANCE_NAME}"
                RESULT_REF["INSTANCE_CONFIG_PATH"]="${INIT_SYSTEM_CONFIG_PATH}"
                RESULT_REF["DISPLAY_NUMBER"]="${VNCD_INSTANCE_DISPLAY_NUMBER}"
                return 0
            else
                if (( "${DISPLAY_NUMBER} < ${VNCD_INSTANCE_DISPLAY_NUMBER}" )); then
                    DISPLAY_NUMBER="${VNCD_INSTANCE_DISPLAY_NUMBER}"
                fi
            fi
        fi
    done
    DISPLAY_NUMBER="$(("${DISPLAY_NUMBER} + 1"))"
    local VNCD_INSTANCE_NAME="${VNCD_BASENAME}@${VNC_USER}-${DISPLAY_NUMBER}.service"
    local VNCD_INSTANCE_CONFIG_PATH="${INIT_SYSTEM_BASE_DIR_PATH}/${VNCD_INSTANCE_NAME}"
    RESULT_REF["INSTANCE_NAME"]="${VNCD_INSTANCE_NAME}"
    RESULT_REF["INSTANCE_CONFIG_PATH"]="${VNCD_INSTANCE_CONFIG_PATH}"
    RESULT_REF["DISPLAY_NUMBER"]="${DISPLAY_NUMBER}"
    return 0
}


function vnc_server_create_systemd_config() {
    local -n VNC_SERVER_CONFIG_REF=${1}

    local VNC_USER="${VNC_SERVER_CONFIG_REF["USER"]}"
    local VNC_SERVER_EXECUTABLE_PATH="${VNC_SERVER_CONFIG_REF["EXECUTABLE_PATH"]}"
    local VNC_DISPLAY=":${VNC_SERVER_CONFIG_REF["DISPLAY_NUMBER"]}"
    local VNCD_INSTANCE_CONFIG_PATH="${VNC_SERVER_CONFIG_REF["INSTANCE_CONFIG_PATH"]}"

    # https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html#Options
    # https://www.digitalocean.com/community/tutorials/how-to-install-and-configure-vnc-on-ubuntu-22-04
    # https://wiki.archlinux.org/title/Systemd_(%D0%A0%D1%83%D1%81%D1%81%D0%BA%D0%B8%D0%B9)#%D0%A2%D0%B8%D0%BF%D1%8B_%D1%81%D0%BB%D1%83%D0%B6%D0%B1
    # https://wiki.archlinux.org/title/TigerVNC#With_a_user_service
    fs_create_file "[Unit]
Description=Start VNC server at startup

[Service]
Type=forking

ExecStartPre=-${VNC_SERVER_EXECUTABLE_PATH} -kill ${VNC_DISPLAY} > /dev/null 2>&1
ExecStart=${VNC_SERVER_EXECUTABLE_PATH} -localhost no ${VNC_DISPLAY}
ExecStop=${VNC_SERVER_EXECUTABLE_PATH} -kill ${VNC_DISPLAY}

[Install]
WantedBy=default.target" "${VNCD_INSTANCE_CONFIG_PATH}" "${VNC_USER}" || return $?
    return 0
}

function vnc_server_create_runit_config() {
    local -n VNC_SERVER_CONFIG_REF=${1}

    local VNC_SERVER_EXECUTABLE_PATH="${VNC_SERVER_CONFIG_REF["EXECUTABLE_PATH"]}"
    local VNC_DISPLAY=":${VNC_SERVER_CONFIG_REF["DISPLAY_NUMBER"]}"
    local VNCD_INSTANCE_NAME="${VNC_SERVER_CONFIG_REF["INSTANCE_NAME"]}"

    runit_create_run_file "${VNCD_INSTANCE_NAME}" \
"#!${SHELL}
${VNC_SERVER_EXECUTABLE_PATH} -kill ${VNC_DISPLAY} 2>&1
exec ${VNC_SERVER_EXECUTABLE_PATH} -fg -localhost no ${VNC_DISPLAY} 2>&1 || exit $?
exit 0" || return $?
    return 0
}

function vnc_create_password_if() {
    local VNC_USER_HOME_DIR_PATH="${1}"
    local VNC_USER="${2}"

    if [[ ! -f "${VNC_USER_HOME_DIR_PATH}/.vnc/passwd" ]]; then
        echo "Set VNC password"

        if is_termux; then
            vncpasswd || return $?
        else
            sudo --user="${VNC_USER}" vncpasswd || return $?
        fi
        return 0
    fi

    return 0
}

function vnc_server_setup() {
    if [[ -n "${VNCDESKTOP}" ]]; then
        echo "VNC server is not installed because execution takes place in a VNC session"
        return 0
    fi

    if is_msys; then
        return 0
    fi

    vnc_server_packages_setup || return $?

    local declare -A VNC_SERVER_CONFIG=()
    vnc_server_get_config_info VNC_SERVER_CONFIG "${GLOBAL_CONFIG_VNC_SERVER_USER}" || return $?

    local VNC_USER="${VNC_SERVER_CONFIG["USER"]}"
    local VNCD_INSTANCE_NAME="${VNC_SERVER_CONFIG["INSTANCE_NAME"]}"
    local VNC_XSTARTUP_FILE_PATH="${VNC_SERVER_CONFIG["XSTARTUP_FILE_PATH"]}"
    local VNC_USER_HOME_DIRECTORY_PATH="${VNC_SERVER_CONFIG["USER_HOME_DIRECTORY_PATH"]}"

    service_disable "${VNCD_INSTANCE_NAME}" "${VNC_USER}"

    vnc_server_create_xstartup "${VNC_USER}" "${VNC_XSTARTUP_FILE_PATH}" || return $?

    if is_termux; then
        vnc_server_create_runit_config VNC_SERVER_CONFIG || return $?
    else
        vnc_server_create_systemd_config VNC_SERVER_CONFIG || return $?
    fi

    vnc_create_password_if "${VNC_USER_HOME_DIRECTORY_PATH}" "${VNC_USER}" || return $?

    service_enable "${VNCD_INSTANCE_NAME}" "${VNC_USER}" || return $?

    if ! service_is_active "${VNCD_INSTANCE_NAME}" "${VNC_USER}"; then
        echo "FATAL: ${VNCD_INSTANCE_NAME} not started"
        return 1
    fi

    # 1) systemd
    # https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html

    # 2) vnc run gui application as root
    # https://forums.debian.net/viewtopic.php?p=569020

    # 3) parse target desktop-entry file
    # https://askubuntu.com/questions/347063/list-all-installed-desktop-environments-in-ubuntu
    # https://docs.fileformat.com/settings/desktop/
    # https://www.freedesktop.org/wiki/Specifications/desktop-entry-spec/
    return 0
}




function main_install_min_packages() {
    make_setup || return $?
    download_setup || return $?
    git_setup || return $?
    user_setup || return $?
    service_setup || return $?
    network_setup || return $?
    firewall_setup || return $?
    pci_setup || return $?
    python_setup || return $?
    startup_setup || return $?
    qemu_setup || return $?
    openvpn_setup || return $?
    cpuid_setup || return $?
    ssh_client_setup || return $?
    ssh_server_setup || return $?

    if is_termux; then
        termux_specific_packages_setup || return $?
    fi
    return 0
}

function main_install_dev_packages() {
    main_install_min_packages || return $?

    dev_packages_setup || return $?
    rdp_client_setup || return $?
    smb_server_setup || return $?
    vnc_client_setup || return $?
    vnc_server_setup || return $?
    telnet_client_setup || return $?
    return 0
}

function main_install_full_packages() {
    main_install_dev_packages || return $?

    package_manager_install_packages "${FULL_PACKAGES}" || return $?

    pycharm_setup # Может быть не скачано из-за политики JetBrains по России
    wine_setup || return $?
    openvpn3_setup || return $?
    waydroid_setup || return $?
    # fixme utopia Для MSYS2 rdp_server_setup || return $?
    return 0
}

function main() {
    package_manager_update_and_upgrade || return $?

    if [[ "${GLOBAL_CONFIG_SETUP_PACKAGES_MODE,,}" == "min" ]]; then
        main_install_min_packages || return $?
    elif [[ "${GLOBAL_CONFIG_SETUP_PACKAGES_MODE,,}" == "dev" ]]; then
        main_install_dev_packages || return $?
    else
        main_install_full_packages || return $?
    fi
    return 0
}


# https://ostechnix.com/bash-variables-shell-scripting/
# https://linuxopsys.com/topics/bash-readarray-with-examples
# https://stackoverflow.com/questions/15691942/print-array-elements-on-separate-lines-in-bash
# https://www.baeldung.com/linux/bash-special-variables
# https://www.baeldung.com/linux/ifs-shell-variable
# https://www.gnu.org/software/bash/manual/bash.html#Arrays
# https://www.gnu.org/software/bash/manual/bash.html#Shell-Parameters
# https://stackoverflow.com/questions/169511/how-do-i-iterate-over-a-range-of-numbers-defined-by-variables-in-bash

#rdp
# 1) service disable
# 2) config /etc/xrdp/startwm.sh as xstartup for vnc
# 3) add xrdp user to ssl-cert group
# 4) service enable
# 5) freerfp for win
# 6) статья по тюнингу xrdp
# https://c-nergy.be/blog/?p=13708
# https://www.cyberithub.com/how-to-install-xrdp-on-ubuntu-22-04-lts-jammy-jellyfish/
# https://forum.altlinux.org/index.php?topic=43501.15
# https://bytexd.com/xrdp-ubuntu/
# https://superuser.com/questions/1539900/slow-ubuntu-remote-desktop-using-xrdp

main
