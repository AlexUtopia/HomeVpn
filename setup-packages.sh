#!/bin/bash

#set -x # Раскомментировать для отладки

PYTHON_VERSION_MIN="3.8"
PYTHON_VERSION="3.10"

# su: termux-tools / util-linux
# sudo: tsu / sudo
# https://github.com/termux/termux-tools/blob/master/scripts/su.in
function is_admin_rights_available() {

    return 0
}

function is_termux() {
    if [[ -n "${TERMUX_VERSION}" ]]; then
        return 0
    fi
    return 1
}

# fixme utopia Проверка минимальной версии питона


RUN_WITH_ADMIN_RIGHTS="sudo"
if is_termux; then
    RUN_WITH_ADMIN_RIGHTS=""
fi

TERMUX_ROOT=""
if is_termux; then
    TERMUX_ROOT="${PREFIX}"
fi


MKDIR="mkdir -p" # fixme utopia to function


SAMBA_PUBLIC_DIRECTORY_PATH="/share"
SAMBA_USERNAME="samba_user_for_home_vpn"
if is_termux; then
    SAMBA_PUBLIC_DIRECTORY_PATH="${TERMUX_ROOT}/share"
fi

SMBD_TCP_PORTS="139 445" # https://unlix.ru/%D0%BD%D0%B0%D1%81%D1%82%D1%80%D0%BE%D0%B9%D0%BA%D0%B0-%D1%84%D0%B0%D0%B5%D1%80%D0%B2%D0%BE%D0%BB%D0%B0-iptables-%D0%B4%D0%BB%D1%8F-samba/
if is_termux; then
    SMBD_TCP_PORTS="1139 4445" # Android не может использовать порты ниже 1024, см. https://android.stackexchange.com/a/205562
fi

### Minimal packages begin

# fixme utopia file, gpg, which, lsb-release (package)

OPEN_VPN_PACKAGE="openvpn"
WGET_PACKAGE="wget"
TAR_PACKAGE="tar"
PROCPS_PACKAGE="procps" # Утилита sysctl для записи параметров ядра linux
IPTABLES_PACKAGE="iptables" # Настройки фaйервола
IPROUTE2_PACKAGE="iproute2" # Утилита ip управления сетевыми интерфейсами
COREUTILS_PACKAGE="coreutils" # Утилита uname, mkdir, echo, mv, chmod, groups, id

PYTHON3_PACKAGE="python3 python3-pip python3-venv"
if is_termux; then
    PYTHON3_PACKAGE="python python-pip"
fi

SSH_CLIENT_PACKAGE="openssh-client"
if is_termux; then
    SSH_CLIENT_PACKAGE="openssh"
fi

DNSMASQ_PACKAGE="dnsmasq-base" # DNS/DHCP сервер для сетевых адаптеров виртуальных машин qemu
if is_termux; then
    DNSMASQ_PACKAGE=""
fi

QEMU_SYSTEM_PACKAGE="qemu qemu-system qemu-kvm"
if is_termux; then
    QEMU_SYSTEM_PACKAGE="qemu-system-x86-64"
fi

MINIMAL_PACKAGES="${OPEN_VPN_PACKAGE} ${WGET_PACKAGE} ${TAR_PACKAGE} ${PROCPS_PACKAGE} ${IPTABLES_PACKAGE} ${IPROUTE2_PACKAGE} ${COREUTILS_PACKAGE} ${PYTHON3_PACKAGE} ${SSH_CLIENT_PACKAGE} ${DNSMASQ_PACKAGE} ${QEMU_SYSTEM_PACKAGE}"
### Minimal packages end


### Development packages begin

GIT_PACKAGE="git"
AUTOCUTSEL_PACKAGE="autocutsel" # Используется для организации буфера обмена для VNC сессии, см. https://superuser.com/a/1524282
NANO_PACKAGE="nano" # Консольный текстовый редактор

SSH_SERVER_PACKAGE="openssh-server"
if is_termux; then
    SSH_SERVER_PACKAGE="openssh"
fi

VNC_CLIENT_PACKAGE="tigervnc-viewer"
VNC_SERVER_PACKAGE="tigervnc-standalone-server tigervnc-xorg-extension"
if is_termux; then
    VNC_SERVER_PACKAGE="tigervnc"
fi

AUXILIARY_UTILITIES="htop cpu-checker util-linux pciutils usbutils lshw" # Утилиты htop kvm-ok, lscpu, lspci, lsusb, lshw
if is_termux; then
    AUXILIARY_UTILITIES="htop util-linux pciutils"
fi

TELNET_CLIENT_PACKAGE="putty" # Для подключения к qemu monitor

SAMBA_PACKAGE="samba"

SYSTEMD_PACKAGE="systemd" # Утилита systemctl
if is_termux; then
    SYSTEMD_PACKAGE="termux-services"
fi

PASSWD_PACKAGE="passwd" # Утилиты usermod, useradd см. https://pkgs.org/download/passwd
if is_termux; then
    PASSWD_PACKAGE=""
fi

DEV_PACKAGES="${MINIMAL_PACKAGES} ${GIT_PACKAGE} ${AUTOCUTSEL_PACKAGE} ${NANO_PACKAGE} ${SSH_SERVER_PACKAGE} ${VNC_CLIENT_PACKAGE} ${VNC_SERVER_PACKAGE} ${AUXILIARY_UTILITIES} ${TELNET_CLIENT_PACKAGE} ${SAMBA_PACKAGE} ${SYSTEMD_PACKAGE} ${PASSWD_PACKAGE}"
### Development packages end


### Full packages begin

DOUBLE_COMMANDER_PACKAGE="doublecmd-qt"
if is_termux; then
    DOUBLE_COMMANDER_PACKAGE=""
fi

MIDNIGHT_COMMANDER_PACKAGE="mc"

XFCE4_PACKAGE=""
if is_termux; then
    XFCE4_PACKAGE="xfce4 xfce4-terminal" # https://wiki.termux.com/wiki/Graphical_Environment
fi

FIREFOX_PACKAGE="firefox"

OPEN_JDK_PACKAGE="openjdk-19-jdk" # Для запуска pycharm IDE
if is_termux; then
    OPEN_JDK_PACKAGE="openjdk-17"
fi

QT_CREATOR_PACKAGE="qtcreator"
if is_termux; then
    QT_CREATOR_PACKAGE="qt-creator"
fi

LIBREOFFICE_PACKAGE="libreoffice"
if is_termux; then
    LIBREOFFICE_PACKAGE=""
fi

FULL_PACKAGES="${DEV_PACKAGES} ${DOUBLE_COMMANDER_PACKAGE} ${MIDNIGHT_COMMANDER_PACKAGE} ${XFCE4_PACKAGE} ${FIREFOX_PACKAGE} ${OPEN_JDK_PACKAGE} ${QT_CREATOR_PACKAGE}"
### Full packages end


PIP_PACKAGES="pystun3==1.0.0 python-iptables==1.0.0 psutil==5.9.1 netaddr==0.8.0 randmac==0.1 transmission-rpc==4.2.0 semantic_version==2.10.0 os-release==1.0.1"


function get_system_name() {
    local RESULT
    RESULT=$(uname -o) || return $?
    echo "${RESULT,,}"
    return 0
}

function make_dirs() {
    mkdir -p "${1}"
    return $?
}

### Download API begin

## @fn get_file_name_from_url()
## @brief Получить имя файла из URL
## @param URL для скачивания
## @retval 0 если успешно
## @return Имя файла из URL
function get_file_name_from_url() {
    local RESULT
    RESULT=$(basename "${1}") || return $?
    echo "${RESULT}"
    return 0
}

## @fn download_file()
## @brief Скачать файл в директорию
## @param URL для скачивания
## @param Директория куда будет скачан файл по URL
## @retval 0 если успешно
function download_file_to_directory() {
    # fixme utopia make directory
    pushd "${2}" || return $?
    wget "${1}" || return $?
    popd || return $?
    return 0
}

### Download API end


### System package manager begin

## @fn is_executable_available()
## @brief Проверить существует ли целевой исполняемый файл
## @details https://stackoverflow.com/a/26759734
## @param Имя исполняемого файла, можно с полный путь до исполняемого файла
## @retval 0 если целевой исполняемый файл существует; 1 - не существует
function is_executable_available() {
    local TARGET_EXECUTABLE_PATH
    TARGET_EXECUTABLE_PATH=$(command -v "${1}") || return $?
    if [[ -x "${TARGET_EXECUTABLE_PATH}" ]]; then
        return 0
    fi
    return 1
}

## @fn package_manager_is_apt()
## @brief Проверить существует ли пакетный менеджер apt
## @details Debian, Ubuntu, Linux Mint, termux
## @retval 0 пакетный менеджер apt существует; 1 - не существует
function package_manager_is_apt() {
    is_executable_available "apt"
    return $?
}

## @fn package_manager_is_pacman()
## @brief Проверить существует ли пакетный менеджер pacman
## @details Arch Linux, MinGW
## @retval 0 пакетный менеджер pacman существует; 1 - не существует
function package_manager_is_pacman() {
    is_executable_available "pacman"
    return $?
}

## @fn package_manager_is_yum()
## @brief Проверить существует ли пакетный менеджер yum
## @details RHEL, Fedora, CentOS
## @retval 0 пакетный менеджер yum существует; 1 - не существует
function package_manager_is_yum() {
    is_executable_available "yum"
    return $?
}

## @fn package_manager_is_dnf()
## @brief Проверить существует ли пакетный менеджер dnf
## @details Fedora
## @retval 0 пакетный менеджер dnf существует; 1 - не существует
function package_manager_is_dnf() {
    is_executable_available "dnf"
    return $?
}

## @fn package_manager_is_zypper()
## @brief Проверить существует ли пакетный менеджер zypper
## @details openSUSE
## @retval 0 пакетный менеджер zypper существует; 1 - не существует
function package_manager_is_zypper() {
    is_executable_available "zypper"
    return $?
}

function get_linux_distro_codename() {
   local RESULT
   RESULT=$(lsb_release -c -s)
   if $?; then
       echo "${RESULT},,"
       return 0
   fi
   echo ""
   return 0
}

function get_linux_mint_underlying_ubuntu_codename_or_normal_codename() {

    return 0
}

function dpkg_get_main_architecture() {
   local RESULT
   RESULT=$(dpkg --print-architecture) || return $?
   echo "${RESULT}"
   return 0
}

## @fn apt_add_sources()
## @brief Добавить source файл в формате deb822 для apt
## @details https://wiki.debian.org/ArchitectureSpecificsMemo
## @param Путь куда сформировать *.source файл
## @param URIs параметр (обязательный)
## @param Suites параметр (обязательный)
## @param Components параметр (обязательный)
## @param Signed-By параметр (не обязательный)
## @param Architectures параметр (не обязательный, будет использована архитектура по умолчанию)
## @param Types параметр (не обязательный, будет "deb")
## @retval 0 - успешное выполнение
function apt_create_sources() {
   local TARGET_SOURCES_FILE_PATH="${1}"
   local URIS="${2}"
   local SUITES="${3}"
   local COMPONENTS="${4}"

   local SIGNED_BY="${5}"
   local SIGNED_BY_PATH=""
   if [[ -n "${SIGNED_BY}" ]]; then
       SIGNED_BY_PATH="Signed-By: \"${SIGNED_BY}\""
   fi

   local ARCHITECTURES="${6}"
   if [[ -z "${ARCHITECTURES}" ]]; then
       ARCHITECTURES=$(dpkg_get_main_architecture) || return $?
   fi

   local TYPES="${7}"
   if [[ -z "${TYPES}" ]]; then
       TYPES="deb"
   fi

${RUN_WITH_ADMIN_RIGHTS} ${SHELL} -c "echo 'Types: ${TYPES}
URIs: ${URIS}
Suites: ${SUITES}
Components: ${COMPONENTS}
Architectures: ${ARCHITECTURES}
${SIGNED_BY_PATH}' > \"${TARGET_SOURCES_FILE_PATH}\"" || return $?
    return 0
}


function apt_download_key() {
    # fixme utopia Просто делаем gpg --dearmor для любого вида ключей, и не заморачиваемся с распознаванием типа файла ключа - это бесполезно

}

function apt_add_sources() {
    NAME="${1}"
    SIGN_FILE_URL="${2}"



}

# fixme utopia https://www.shellhacks.com/linux-mint-find-ubuntu-version-it-is-based-on/

# https://dev.to/henrybarreto/pacman-s-simple-guide-for-apt-s-users-5hc4

function apt_update_and_upgrade() {
    ${RUN_WITH_ADMIN_RIGHTS} apt update || return $?
    ${RUN_WITH_ADMIN_RIGHTS} apt upgrade -y || return $?
    return 0
}

function apt_install_packages() {
    ${RUN_WITH_ADMIN_RIGHTS} apt install ${1} -y || return $?
    return 0
}

function apt_is_package_installed() {
    apt -L ${1}
    return $?
}

function pacman_update_and_upgrade() {
    ${RUN_WITH_ADMIN_RIGHTS} pacman -Syu || return $?
    return 0
}

function pacman_install_packages() {
    ${RUN_WITH_ADMIN_RIGHTS} pacman -S ${1} || return $?
    return 0
}

function pacman_is_package_installed() {
    pacman -Q ${1}
    return $?
}

function package_manager_update_and_upgrade() {
    if package_manager_is_apt; then
        apt_update_and_upgrade || return $?
    elif package_manager_is_pacman; then
        pacman_update_and_upgrade || return $?
    elif package_manager_is_yum; then
        # fixme utopia Дописать
    elif package_manager_is_dnf; then
        # fixme utopia Дописать
    elif package_manager_is_zypper; then
        # fixme utopia Дописать
    else
        echo "FATAL: unknown package manager"
        return 1
    fi
    return 0
}

function package_manager_install_packages() {
    if package_manager_is_apt; then
        apt_install_packages || return $?
    elif package_manager_is_pacman; then
        pacman_install_packages || return $?
    elif package_manager_is_yum; then
        # fixme utopia Дописать
    elif package_manager_is_dnf; then
        # fixme utopia Дописать
    elif package_manager_is_zypper; then
        # fixme utopia Дописать
    else
        echo "FATAL: unknown package manager"
        return 1
    fi
    return 0
}

function package_manager_is_package_installed() {
    if package_manager_is_apt; then
        apt_is_package_installed
        return $?
    elif package_manager_is_pacman; then
        pacman_is_package_installed
        return $?
    elif package_manager_is_yum; then
        # fixme utopia Дописать
    elif package_manager_is_dnf; then
        # fixme utopia Дописать
    elif package_manager_is_zypper; then
        # fixme utopia Дописать
    else
        echo "FATAL: unknown package manager"
        return 1
    fi
    return 0
}

### System package manager end

function update_pip() {
    ${RUN_WITH_ADMIN_RIGHTS} python3 -m pip install pip --force-reinstall --ignore-installed || return $?
    return 0
}

function install_pip_packages() {
    for pip_package in ${1}
    do
      ${RUN_WITH_ADMIN_RIGHTS} pip3 install "${pip_package}" --force-reinstall --ignore-installed || return $?
    done
    return 0
}

### System services begin

function systemd_is_service_active() {
    local SERVICE_IS_RUNNING
    SERVICE_IS_RUNNING=$(systemctl is-active "${1}") || return $?

    if [ "${SERVICE_IS_RUNNING,,}" = "active" ]; then
        return 0
    fi
    return 1
}

function systemd_service_enable() {
    ${RUN_WITH_ADMIN_RIGHTS} systemctl enable "${1}"
    return $?
}

function systemd_service_disable() {
    ${RUN_WITH_ADMIN_RIGHTS} systemctl disable "${1}"
    return $?
}

function termux_is_service_active() {
    # https://manpages.ubuntu.com/manpages/trusty/en/man8/sv.8.html
    local SERVICE_IS_RUNNING
    SERVICE_IS_RUNNING=$(sv status "${1}") || return $?

    if [[ "${SERVICE_IS_RUNNING}" = "run: "* ]]; then # https://stackoverflow.com/a/229606
        return 0
    fi
    return 1
}

function termux_service_enable() {
    ${RUN_WITH_ADMIN_RIGHTS} sv-enable "${1}"
    return $?
}

function termux_service_disable() {
    ${RUN_WITH_ADMIN_RIGHTS} sv-disable "${1}"
    return $?
}

function is_service_active() {
    if is_termux; then
        termux_is_service_active "${1}"
        return $?
    fi

    systemd_is_service_active "${1}"
    return $?
}

function service_enable() {
    if is_termux; then
        termux_service_enable "${1}"
        return $?
    fi

    systemd_service_enable "${1}"
    return $?
}

function service_disable() {
    if is_termux; then
        termux_service_disable "${1}"
        return $?
    fi

    systemd_service_disable "${1}"
    return $?
}

### System services end


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


### User API begin

function user_add() {
    ${RUN_WITH_ADMIN_RIGHTS} useradd "${1}"
    return $?
}

function user_is_available() {
    id "${1}"
    return $?
}

function user_add_to_group() {
    ${RUN_WITH_ADMIN_RIGHTS} usermod -a -G "${2}" "${1}"
    return $?
}

function user_is_added_to_group() {
    local USER_GROUP_NAME_LIST
    USER_GROUP_NAME_LIST=$(id "${1}" -G -n) || return $? # https://www.geeksforgeeks.org/how-to-check-the-groups-a-user-belongs-to-in-linux/
    for USER_GROUP_NAME in USER_GROUP_NAME_LIST
    do
      if [ "${USER_GROUP_NAME}" = "${2}" ]; then
          return 0
      fi
    done
    return 1
}

### User API end


function setup_sshd() {
    local SSHD="sshd"
    if is_service_active "${SSHD}"; then
      return 0
    fi
    service_enable "${SSHD}" || return $?
    return 0
}

function install_pycharm() {
    # https://www.jetbrains.com/edu-products/download/other-PCE.html
    # Текущая версия 2023.2.3 (Community Edition)
    # fixme utopia Реализовать
    return 0
}

function termux_install_rdp_client() {
    package_manager_install_packages "freerdp"
    return $?
}

function install_rdp_client() {
    if is_termux; then
        termux_install_rdp_client || return $?
        return 0
    fi

    # 0) naming for package *.source file
    # 1) check *.sources file in /etc/apt/sources.list.d/
    # 2) download key
    # 3) gpg --dearmor key if need (/etc/apt/keyrings) [gnupg package]
    # 4) make *.sources file in /etc/apt/sources.list.d/
    # 5) apt update
    # 6) install_packages

    # https://interface31.ru/tech_it/2022/09/apt-key-is-deprecated-ili-upravlenie-klyuchami-v-sovremennyh-vypuskah-debian-i-ubunt.html
    # https://habr.com/en/articles/683716/

    # https://pub.freerdp.com/releases/
    # https://github.com/FreeRDP/FreeRDP
    # fixme utopia Реализовать
    # https://ci.freerdp.com/job/freerdp-nightly-binaries/
    # echo "FreeRDP installed to <directory>, see https://github.com/FreeRDP/FreeRDP/wiki/CommandLineInterface"
    return 0
}

function install_wine() {
    # https://wiki.winehq.org/Ubuntu
    return 0
}

function get_smbd_config_file_path() {
    local SMBD_BUILD_OPTIONS
    SMBD_BUILD_OPTIONS=$(smbd -b) || return $?

    local SMBD_CONFIG_FILE_PATH
    SMBD_CONFIG_FILE_PATH=$(echo "${SMBD_BUILD_OPTIONS}" | sed -En 's/^[\t ]*CONFIGFILE:[\t ]+(.*)$/\1/p') || return $? # https://stackoverflow.com/a/43997253

    echo "${SMBD_CONFIG_FILE_PATH}"
    return 0
}

function make_samba_user_and_assign_rights() {
    if ! is_termux; then
        # https://askubuntu.com/questions/97669/i-cant-get-samba-to-set-proper-permissions-on-created-directories
        local SAMBASHARE_GROUP="sambashare"

        if ! user_is_available "${SAMBA_USERNAME}"; then
            user_add "${SAMBA_USERNAME}" || return $?
        fi

        if ! user_is_added_to_group "${SAMBA_USERNAME}" "${SAMBASHARE_GROUP}"; then
            user_add_to_group "${SAMBA_USERNAME}" "${SAMBASHARE_GROUP}" || return $?
        fi
        return 0
    fi
    return 0
}

function make_samba_public_directory() {
    ${RUN_WITH_ADMIN_RIGHTS} ${MKDIR} "${SAMBA_PUBLIC_DIRECTORY_PATH}" || return $?
    ${RUN_WITH_ADMIN_RIGHTS} chmod 0777 "${SAMBA_PUBLIC_DIRECTORY_PATH}" || return $?
    return 0
}

function make_smbd_config() {
    # https://www.samba.org/samba/docs/current/man-html/smb.conf.5.html

    local SMBD_CONFIG_FILE_PATH
    SMBD_CONFIG_FILE_PATH=$(get_smbd_config_file_path) || return $?

    local SMBD_CONFIG_FILE_DIR_PATH
    SMBD_CONFIG_FILE_DIR_PATH=$(dirname "${SMBD_CONFIG_FILE_PATH}") || return $?

    local SMBD_CONFIG_FILE_NAME
    SMBD_CONFIG_FILE_NAME=$(basename "${SMBD_CONFIG_FILE_PATH}") || return $?

    ${RUN_WITH_ADMIN_RIGHTS} ${MKDIR} "${SMBD_CONFIG_FILE_DIR_PATH}" || return $?

    if [ -f "${SMBD_CONFIG_FILE_PATH}" ]; then
        local CURRENT_DATE_TIME
        CURRENT_DATE_TIME=$(date +%Y-%m-%dT%H_%M_%S_%N%z) || return $?
        local OLD_SMBD_CONFIG_FILE_DIR_PATH="${SMBD_CONFIG_FILE_DIR_PATH}/unused_since_${CURRENT_DATE_TIME}_${SMBD_CONFIG_FILE_NAME}"
        echo "smbd config file exist (${SMBD_CONFIG_FILE_PATH}), rename to ${OLD_SMBD_CONFIG_FILE_DIR_PATH}"
        sudo mv "${SMBD_CONFIG_FILE_PATH}" ${OLD_SMBD_CONFIG_FILE_DIR_PATH}
    fi

    # https://www.samba.org/samba/docs/using_samba/ch08.html#samba2-CHP-8-TABLE-2
    ${RUN_WITH_ADMIN_RIGHTS} ${SHELL} -c "echo '[global]
workgroup = WORKGROUP
security = user
map to guest = bad user
wins support = no
dns proxy = no
smb ports = ${SMBD_TCP_PORTS}
inherit permissions = yes

[public]
path = \"${SAMBA_PUBLIC_DIRECTORY_PATH}\"
guest ok = yes
force user = nobody
browsable = yes
writable = yes
' > \"${SMBD_CONFIG_FILE_PATH}\"" || return $?
    return 0
}

function setup_smbd() {
    # https://ubuntu.com/tutorials/install-and-configure-samba#1-overview
    local SMBD="smbd"

    service_disable "${SMBD}" || return $?

    # make_samba_user_and_assign_rights || return $?
    make_samba_public_directory || return $?
    make_smbd_config || return $?

    service_enable "${SMBD}" || return $?

    if ! is_service_active "${SMBD}"; then
      echo "FATAL: ${SMBD} not started"
    fi

    # https://www.samba.org/~tpot/articles/firewall.html
    # https://ixnfo.com/iptables-pravila-dlya-samba.html
    # https://unlix.ru/%D0%BD%D0%B0%D1%81%D1%82%D1%80%D0%BE%D0%B9%D0%BA%D0%B0-%D1%84%D0%B0%D0%B5%D1%80%D0%B2%D0%BE%D0%BB%D0%B0-iptables-%D0%B4%D0%BB%D1%8F-samba/
    # https://entnet.ru/server/domain/ustanovka-i-nastrojka-samba-server.html
    return 0
}

function setup_vnc_server() {
    # fixme utopia Реализовать
    #!/bin/bash
    ##autocutsel -fork
    #unset SESSION_MANAGER
    #unset DBUS_SESSION_BUS_ADDRESS
    #cinnamon-session-cinnamon
    return 0
}

#package_manager_update_and_upgrade || exit $?

#package_manager_install_packages "${DEV_PACKAGES}" || exit $?

#update_pip || exit $?

#install_pip_packages "${PIP_PACKAGES}" || exit $?

#install_rdp_client || exit $?

#install_pycharm || exit $?

#setup_sshd || exit $?

setup_smbd || exit $?

#setup_vnc_server || exit $?
