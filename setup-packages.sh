#!/bin/bash

# Понять что мы исполняемся внутри вирт машины
# https://unix.stackexchange.com/questions/89714/easy-way-to-determine-the-virtualization-technology-of-a-linux-machine

# fixme utopia VNC сервер для Windows
# fixme utopia RDP сервер для Linux / Android/termux
# fixme utopia Проверка минимальной версии питона
# fixme utopia Установка дополнений гостевой ОС?? требуется ли
# fixme utopia Настройка nmbd
# fixme utopia gvfs для Android/termux
# fixme utopia Инструкция по scp

# fixme utopia Настройка микрофона в браузере
# Звук с микрофона использовать для браузера, например (не забыть выдать разрешение на микрофон для Termux:API, проверть точно ли нужно это разрешение)
# $PREFIX/etc/pulse/default.pa
# load-module module-sles-source
# https://github.com/termux/termux-app/issues/1448
# https://www.reddit.com/r/termux/comments/icp29x/help_using_pulseaudio_on_termux/

# https://unix.stackexchange.com/a/306115

set -x # Раскомментировать для отладки


# su: termux-tools / util-linux
# sudo: tsu / sudo
# https://github.com/termux/termux-tools/blob/master/scripts/su.in
function is_admin_rights_available() {
    su --version || return $?
    return 0
}

function is_termux() {
    if [[ -n "${TERMUX_VERSION}" ]]; then
        return 0
    fi
    return 1
}

### Global config begin

GLOBAL_CONFIG_SETUP_PACKAGES_MODE="full" # min, dev, full

GLOBAL_CONFIG_ROOT_PREFIX=""
if is_termux; then
    GLOBAL_CONFIG_ROOT_PREFIX="${PREFIX}/.."
fi

GLOBAL_CONFIG_USR_PREFIX="/usr"
if is_termux; then
    GLOBAL_CONFIG_USR_PREFIX="${PREFIX}"
fi

GLOBAL_CONFIG_ETC_PREFIX="/etc"
if is_termux; then
    GLOBAL_CONFIG_ETC_PREFIX="${GLOBAL_CONFIG_USR_PREFIX}/etc"
fi

GLOBAL_CONFIG_VNC_USER=$(logname) # в termux переменная окружения USER не установлена
GLOBAL_CONFIG_SAMBA_USER=$(logname) # в termux переменная окружения USER не установлена

GLOBAL_CONFIG_SAMBA_PUBLIC_DIRECTORY_PATH="${GLOBAL_CONFIG_ROOT_PREFIX}/smb_share_public"
GLOBAL_CONFIG_SMBD_TCP_PORTS="139 445" # https://unlix.ru/%D0%BD%D0%B0%D1%81%D1%82%D1%80%D0%BE%D0%B9%D0%BA%D0%B0-%D1%84%D0%B0%D0%B5%D1%80%D0%B2%D0%BE%D0%BB%D0%B0-iptables-%D0%B4%D0%BB%D1%8F-samba/
if is_termux; then
    GLOBAL_CONFIG_SMBD_TCP_PORTS="1139 4445" # Android не может использовать порты ниже 1024, см. https://android.stackexchange.com/a/205562
fi

### Global config end


### termux specific packages begin

TERMUX_SPECIFIC_PACKAGES="termux-tools termux-api proot"

### termux specific packages end


### Minimal packages begin

OPEN_VPN_PACKAGE="openvpn"
if is_termux; then
    OPEN_VPN_PACKAGE=""
fi
WGET_PACKAGE="wget"
TAR_PACKAGE="tar"
PROCPS_PACKAGE="procps" # Утилита sysctl для записи параметров ядра linux
IPTABLES_PACKAGE="iptables" # Настройки фaйервола
IPROUTE2_PACKAGE="iproute2" # Утилита ip управления сетевыми интерфейсами
COREUTILS_PACKAGE="coreutils" # Утилита uname, mkdir, echo, mv, chmod, groups, id, sort, logname
GPG_PACKAGE="gnupg"
FINDUTILS_PACKAGE="findutils" # Утилита find
PCREGREP_PACKAGE="pcregrep" # https://packages.msys2.org/package/mingw-w64-x86_64-pcre
WHICH_PACKAGE="debianutils"
if is_termux; then
    WHICH_PACKAGE="which"
fi
MAKE_PACKAGE="make"

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

MINIMAL_PACKAGES="${OPEN_VPN_PACKAGE} ${WGET_PACKAGE} ${TAR_PACKAGE} ${PROCPS_PACKAGE} ${IPTABLES_PACKAGE} ${IPROUTE2_PACKAGE} ${COREUTILS_PACKAGE} ${GPG_PACKAGE} ${FINDUTILS_PACKAGE} ${PCREGREP_PACKAGE} ${PYTHON3_PACKAGE} ${SSH_CLIENT_PACKAGE} ${DNSMASQ_PACKAGE} ${QEMU_SYSTEM_PACKAGE} ${WHICH_PACKAGE} ${MAKE_PACKAGE}"
if is_termux; then
    MINIMAL_PACKAGES="${MINIMAL_PACKAGES} ${TERMUX_SPECIFIC_PACKAGES}"
fi

### Minimal packages end


### Development packages begin

GIT_PACKAGE="git"
AUTOCUTSEL_PACKAGE="autocutsel" # Используется для организации буфера обмена для VNC сессии, см. https://superuser.com/a/1524282
if is_termux; then
    AUTOCUTSEL_PACKAGE=""
fi

NANO_PACKAGE="nano" # Консольный текстовый редактор

XFCE4_PACKAGE=""
if is_termux; then
    XFCE4_PACKAGE="xfce4 xfce4-terminal" # https://wiki.termux.com/wiki/Graphical_Environment
fi

RDP_SERVER_PACKAGE="xrdp"

SSH_SERVER_PACKAGE="openssh-server"
if is_termux; then
    SSH_SERVER_PACKAGE="openssh"
fi

VNC_CLIENT_PACKAGE="tigervnc-viewer"
VNC_SERVER_PACKAGE="tigervnc-standalone-server tigervnc-xorg-extension x11-xserver-utils" # x11-xserver-utils - Debian/Ubuntu only https://pkgs.org/search/?q=x11-xserver-utils
if is_termux; then
    VNC_SERVER_PACKAGE="tigervnc xorg-xhost"
fi

AUXILIARY_UTILITIES="htop cpu-checker util-linux pciutils usbutils lshw" # Утилиты htop kvm-ok, lscpu, lspci, lsusb, lshw
if is_termux; then
    AUXILIARY_UTILITIES="htop util-linux pciutils"
fi

TELNET_CLIENT_PACKAGE="putty" # Для подключения к qemu monitor

SAMBA_PACKAGE="samba"

SERVICES_SUPERVISOR_PACKAGE= # "systemd" # Утилита systemctl
if is_termux; then
    SERVICES_SUPERVISOR_PACKAGE="termux-services"
fi

PASSWD_PACKAGE="passwd" # Утилиты usermod, useradd см. https://pkgs.org/download/passwd
if is_termux; then      # passwd для настройки доступа к ssh серверу по паролю
    PASSWD_PACKAGE="termux-auth"
fi

DEV_PACKAGES="${MINIMAL_PACKAGES} ${GIT_PACKAGE} ${AUTOCUTSEL_PACKAGE} ${NANO_PACKAGE} ${XFCE4_PACKAGE} ${RDP_SERVER_PACKAGE} ${SSH_SERVER_PACKAGE} ${PASSWD} ${VNC_CLIENT_PACKAGE} ${VNC_SERVER_PACKAGE} ${AUXILIARY_UTILITIES} ${TELNET_CLIENT_PACKAGE} ${SAMBA_PACKAGE} ${SERVICES_SUPERVISOR_PACKAGE} ${PASSWD_PACKAGE}"
### Development packages end


### Full packages begin

DOUBLE_COMMANDER_PACKAGE="doublecmd-qt"
if is_termux; then
    DOUBLE_COMMANDER_PACKAGE=""
fi

MIDNIGHT_COMMANDER_PACKAGE="mc"

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

TRANSMISSION_PACKAGE="transmission"

FULL_PACKAGES="${DEV_PACKAGES} ${DOUBLE_COMMANDER_PACKAGE} ${MIDNIGHT_COMMANDER_PACKAGE} ${FIREFOX_PACKAGE} ${OPEN_JDK_PACKAGE} ${QT_CREATOR_PACKAGE} ${LIBREOFFICE_PACKAGE} ${TRANSMISSION_PACKAGE}"
### Full packages end


PIP_PACKAGES="pystun3==1.0.0 python-iptables==1.0.0 psutil==5.9.1 netaddr==0.8.0 randmac==0.1 transmission-rpc==4.2.0 semantic_version==2.10.0 os-release==1.0.1"

### System API begin

function get_os_name() {
    local RESULT=""
    RESULT=$(uname -o) || return $?
    echo "${RESULT,,}"
    return 0
}

function is_linux() {
  local SYSTEM_NAME=""
  SYSTEM_NAME=$(get_os_name) || return $?

   if [[ "${SYSTEM_NAME}" == *"linux"* ]]; then
       return 0
   fi
   return 1
}

function is_msys() {
  local SYSTEM_NAME=""
  SYSTEM_NAME=$(get_os_name) || return $?

   if [[ "${SYSTEM_NAME}" == *"msys"* ]]; then
       return 0
   fi
   return 1
}

function is_cygwin() {
  local SYSTEM_NAME=""
  SYSTEM_NAME=$(get_os_name) || return $?

   if [[ "${SYSTEM_NAME}" == *"cygwin"* ]]; then
       return 0
   fi
   return 1
}

function get_os_distro_name() {
   local OS_RELEASE_PATH="${GLOBAL_CONFIG_ETC_PREFIX}/os-release"

   . "${OS_RELEASE_PATH}" || return $?

   if [[ -n "${UBUNTU_CODENAME}" ]]; then
       # Для Ubuntu-based дистрибутивов linux (типа Linix Mint) всегда используются ubuntu PPA
       echo "ubuntu"
   else
       echo "${ID}"
   fi
   return 0
}

function get_os_distro_codename_or_version() {
   local OS_RELEASE_PATH="${GLOBAL_CONFIG_ETC_PREFIX}/os-release"

   . "${OS_RELEASE_PATH}" || return $?

   if [[ -n "${UBUNTU_CODENAME}" ]]; then
       echo "${UBUNTU_CODENAME}"
   elif [[ -n "${VERSION_CODENAME}" ]]; then
       echo "${VERSION_CODENAME}"
   else
       echo "${VERSION_ID}"
   fi
   return 0
}

function make_dirs() {
    local DIR_PATH="${1}"

    mkdir -p "${DIR_PATH}" > "/dev/null" || return $?
    return 0
}

function wait_for_dir_creation() {
   local TARGET_DIR_PATH="${1}"
   local WAIT_SECONDS_COUNT=${2}
   if [[ -z "${WAIT_SECONDS_COUNT}" ]]; then
        WAIT_SECONDS_COUNT=10
    fi

   for (( i = 0; i < WAIT_SECONDS_COUNT; i++ )); do
       if [[ -d "${TARGET_DIR_PATH}" ]]; then
           return 0
       fi
       sleep 1
   done
   return 1
}

function create_symlink() {
    local SOURCE_PATH="${1}"
    local TARGET_PATH="${2}"

    # В termux почему-то опция -f у ln не всегда срабатывает, поэтому удалим символическую ссылку вручную
    rm -rf "${TARGET_PATH}" > "/dev/null" || return $?
    ln -s "${SOURCE_PATH}" "${TARGET_PATH}" > "/dev/null" || return $?
    return 0
}

function check_result_code() {
    return ${1}
}

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

    local MAXDEPTH=1
    local NULL_SYMBOL=$'\0'

    while IFS= read -r -d "${NULL_SYMBOL}" FILE_PATH; do
        # echo "${FILE_PATH}" fixme utopia del?
        RESULT_REF+=("${FILE_PATH}")
    done < <(find "${DIR_PATH}" -maxdepth ${MAXDEPTH} -name "${PATH_WILDCARDS}" -type "${TYPE}" -print0 | sort -z -V)
    return 0
}

function set_file_as_executable() {
    local FILE_PATH="${1}"
    chmod +x "${FILE_PATH}" > "/dev/null" || return $?
    return 0
}

### System API end


### Misc API begin

function deactivate_file_if_exists() {
    local FILE_PATH="${1}"

    if [[ -f "${FILE_PATH}" ]]; then
        local CURRENT_DATE_TIME=""
        CURRENT_DATE_TIME=$(date "+%Y-%m-%dT%H_%M_%S_%N%z") || return $?

        local FILE_NAME=""
        FILE_NAME=$(basename "${FILE_PATH}") || return $?

        local FILE_DIR_PATH=""
        FILE_DIR_PATH=$(dirname "${FILE_PATH}") || return $?

        local DEACTIVATE_FILE_PATH="${FILE_DIR_PATH}/unused_since_${CURRENT_DATE_TIME}_${FILE_NAME}"
        echo "File exist (\"${FILE_PATH}\"), rename to \"${DEACTIVATE_FILE_PATH}\""
        mv "${FILE_PATH}" "${DEACTIVATE_FILE_PATH}" || return $?
    fi
}

function prepare_for_create_file() {
    local FILE_PATH="${1}"
    local REWRITE_IF_EXIST="${2}"

    local FILE_DIR_PATH=""
    FILE_DIR_PATH=$(dirname "${FILE_PATH}") || return $?

    make_dirs "${FILE_DIR_PATH}" || return $?

    if [[ -z "${REWRITE_IF_EXIST}" ]]; then
        deactivate_file_if_exists "${FILE_PATH}" || return $?
    fi
    return 0
}

function create_file() {
    local CONTENT="${1}"
    local FILE_PATH="${2}"
    local REWRITE_IF_EXIST="${3}"

    prepare_for_create_file "${FILE_PATH}" "${REWRITE_IF_EXIST}" || return $?

    ${SHELL} -c "echo '${CONTENT}' > \"${FILE_PATH}\"" || return $?
    return 0
}

### Misc API end


### Download API begin

## @fn get_file_name_from_url()
## @brief Получить имя файла из URL
## @param URL для скачивания
## @retval 0 если успешно
## @return Имя файла из URL
function get_file_name_from_url() {
    local RESULT=""
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
    local URL="${1}"
    local DIRECTORY_PATH="${2}"

    make_dirs "${DIRECTORY_PATH}" || return $?
    pushd "${DIRECTORY_PATH}" || return $?
    wget "${URL}" || return $?
    popd || return $?
    return 0
}

## @fn download_file()
## @brief Скачать файл
## @param URL для скачивания
## @param Путь до скачанного файла по URL; можно передать "-" - записать результат в stdout
## @retval 0 если успешно
function download_file() {
    local URL="${1}"
    local FILE_PATH="${2}"
    local FILE_DIRECTORY_PATH=""
    FILE_DIRECTORY_PATH=$(dirname "${FILE_PATH}") || return $?

    make_dirs "${FILE_DIRECTORY_PATH}" || return $?
    wget -O "${FILE_PATH}" "${URL}" || return $?
    return 0
}

### Download API end



### User API begin

function user_get_current() {
   local RESULT=""
   RESULT=$(whoami) || return $?
   echo "${RESULT}"
   return 0
}

function user_add() {
    useradd "${1}" > "/dev/null" || return $?
    return 0
}

function user_is_available() {
    local USER_NAME="${1}"

    id "${USER_NAME}" &> "/dev/null" || return $?
    return 0
}

function user_add_to_group() {
    local USER_NAME="${1}"
    local GROUP_NAME="${2}"

    usermod -a -G "${GROUP_NAME}" "${USER_NAME}" > "/dev/null" || return $?
    return 0
}

function user_is_added_to_group() {
    local USER_NAME="${1}"
    local GROUP_NAME="${2}"

    local USER_GROUP_NAME_LIST=""
    USER_GROUP_NAME_LIST=$(id "${USER_NAME}" -G -n 2> "/dev/null") || return $? # https://www.geeksforgeeks.org/how-to-check-the-groups-a-user-belongs-to-in-linux/
    for USER_GROUP_NAME in USER_GROUP_NAME_LIST; do
        if [[ "${USER_GROUP_NAME,,}" == "${GROUP_NAME,,}" ]]; then
            return 0
        fi
    done
    return 1
}

function user_check_and_correct() {
   local USER_NAME="${1}"

    if [[ -z "${USER_NAME}" ]]; then
        USER_NAME=$(user_get_current) || return $?
    fi

    if ! user_is_available "${USER_NAME}"; then
        return 1
    fi

    echo "${USER_NAME}"
    return 0
}

# https://unix.stackexchange.com/a/758316
function user_get_home_directory_path() {
    if is_termux; then # В termux возможен только один пользователь https://wiki.termux.com/wiki/Differences_from_Linux
        echo ~
        return 0
    fi

    local USER_NAME="${1}"
    USER_NAME=$(user_check_and_correct "${USER_NAME}") || return $?

    eval echo "~${USER_NAME}"
    return 0
}

function user_is_set_password() {
    local USER_NAME="${1}"

    USER_NAME=$(user_check_and_correct "${USER_NAME}") || return $?

    if is_termux; then
        local USER_HOME_DIR_PATH=""
        USER_HOME_DIR_PATH=$(user_get_home_directory_path "${USER_NAME}") || return $?
        # https://github.com/termux/termux-auth/blob/master/termux-auth.h#L13C30-L13C41
        local USER_PASSWORD_FILE_PATH="${USER_HOME_DIR_PATH}/.termux_authinfo"
        if [[ -f "$USER_PASSWORD_FILE_PATH" ]]; then
            return 0
        fi
        return 1
    fi

    passwd --status "${USER_NAME}" &> "/dev/null" || return $?
    return 0
}

function user_create_password_if() {
    local USER_NAME="${1}"

    USER_NAME=$(user_check_and_correct "${USER_NAME}") || return $?

    if ! user_is_set_password "${USER_NAME}"; then
        echo "Set password for \"${USER_NAME}\""
        passwd "${USER_NAME}" || return $?
        return 0
    fi

    return 0
}

### User API end


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
    is_executable_available "apt" || return $?
    return 0
}

## @fn package_manager_is_pacman()
## @brief Проверить существует ли пакетный менеджер pacman
## @details Arch Linux, MSYS2
## @retval 0 пакетный менеджер pacman существует; 1 - не существует
function package_manager_is_pacman() {
    is_executable_available "pacman" || return $?
    return 0
}

## @fn package_manager_is_yum()
## @brief Проверить существует ли пакетный менеджер yum
## @details RHEL, Fedora, CentOS
## @retval 0 пакетный менеджер yum существует; 1 - не существует
function package_manager_is_yum() {
    is_executable_available "yum" || return $?
    return 0
}

## @fn package_manager_is_dnf()
## @brief Проверить существует ли пакетный менеджер dnf
## @details Fedora
## @retval 0 пакетный менеджер dnf существует; 1 - не существует
function package_manager_is_dnf() {
    is_executable_available "dnf" || return $?
    return 0
}

## @fn package_manager_is_zypper()
## @brief Проверить существует ли пакетный менеджер zypper
## @details openSUSE
## @retval 0 пакетный менеджер zypper существует; 1 - не существует
function package_manager_is_zypper() {
    is_executable_available "zypper" || return $?
    return 0
}

function dpkg_get_main_architecture() {
   local RESULT=""
   RESULT=$(dpkg --print-architecture) || return $?
   echo "${RESULT}"
   return 0
}

function apt_update_and_upgrade() {
    # https://wiki.debian.org/Multiarch/HOWTO
    # https://wiki.ubuntu.com/MultiarchCross
    dpkg --add-architecture i386 || return $? # Для установки wine требуется добавить i386 архитектуру
    apt update || return $?
    apt upgrade -o Dpkg::Options::="--force-confnew" -y || return $?
    apt update || return $?

    if is_termux; then
        apt -y install x11-repo root-repo || return $?
        apt update || return $?
    fi

    return 0
}

function apt_install_packages() {
    apt -y install ${1} || return $?
    return 0
}

function apt_is_package_installed() {
    apt -L ${1}
    return $?
}



## @fn apt_create_sources()
## @brief Добавить source файл в формате deb822 для apt
## @details https://wiki.debian.org/ArchitectureSpecificsMemo
## @details https://manpages.ubuntu.com/manpages/xenial/man5/sources.list.5.html
## @param Путь куда сформировать *.source файл
## @param URIs параметр (обязательный)
## @param Suites параметр (обязательный)
## @param Components параметр (обязательный)
## @param Signed-By параметр (не обязательный)
## @param Architectures параметр (не обязательный, будет использована архитектура по умолчанию)
## @param Types параметр (не обязательный, будет "deb")
## @retval 0 - успешное выполнение
function apt_create_sources() {
   local SOURCES_FILE_PATH="${1}"
   local URIS="${2}"
   local SUITES="${3}"
   local COMPONENTS="${4}"

   local SIGNED_BY="${5}"
   local SIGNED_BY_PATH=""
   if [[ -n "${SIGNED_BY}" ]]; then
       SIGNED_BY_PATH="Signed-By: ${SIGNED_BY}"
   fi

   local ARCHITECTURES="${6}"
   if [[ -z "${ARCHITECTURES}" ]]; then
       ARCHITECTURES=$(dpkg_get_main_architecture) || return $?
   fi

   local TYPES="${7}"
   if [[ -z "${TYPES}" ]]; then
       TYPES="deb"
   fi

   create_file "Types: ${TYPES}
URIs: ${URIS}
Suites: ${SUITES}
Components: ${COMPONENTS}
Architectures: ${ARCHITECTURES}
${SIGNED_BY_PATH}" "${SOURCES_FILE_PATH}" || return $?
    return 0
}


function apt_get_key_file_path() {
   local KEYRINGS_DIR_PATH="${GLOBAL_CONFIG_ETC_PREFIX}/apt/keyrings"

   local NAME="${1}"

   echo "${KEYRINGS_DIR_PATH}/${NAME}.gpg"
   return 0
}

function apt_get_source_file_path() {
   local APT_SOURCES_LIST_DIR_PATH="${GLOBAL_CONFIG_ETC_PREFIX}/apt/sources.list.d"

   local NAME="${1}"

   echo "${APT_SOURCES_LIST_DIR_PATH}/${NAME}.sources"
   return 0
}

function apt_download_key() {
    local NAME="${1}"
    local KEY_FILE_URL="${2}"

    if [[ -z "${KEY_FILE_URL}" ]]; then
        echo ""
        return 0
    fi

    local KEY_FILE_PATH
    KEY_FILE_PATH=$(apt_get_key_file_path "${NAME}") || return $?

    if [[ -f "${KEY_FILE_PATH}" ]]; then
        echo "${KEY_FILE_PATH}"
        return 0
    fi

    download_file "${KEY_FILE_URL}" "-" | gpg --dearmor > "${KEY_FILE_PATH}" || return $?
    echo "${KEY_FILE_PATH}"
    return 0
}

function apt_add_sources() {
    local NAME="${1}"
    local KEY_FILE_URL="${2}"
    local URIS="${3}"
    local SUITES="${4}"
    local COMPONENTS="${5}"
    local ARCHITECTURES="${6}"
    local TYPES="${7}"

    local SOURCE_FILE_PATH
    SOURCE_FILE_PATH=$(apt_get_source_file_path "${NAME}") || return $?
    if [[ -f "${SOURCE_FILE_PATH}" ]]; then
        echo "WARNING: \"${SOURCE_FILE_PATH}\" already exists"
        return 0
    fi

    local KEY_FILE_PATH
    KEY_FILE_PATH=$(apt_download_key "${NAME}" "${KEY_FILE_URL}") || return $?

    apt_create_sources "${SOURCE_FILE_PATH}" "${URIS}" "${SUITES}" "${COMPONENTS}" "${KEY_FILE_PATH}" "${ARCHITECTURES}" "${TYPES}" || return $?

    apt update
    local APT_UPDATE_RESULT=$?
    if ! check_result_code ${APT_UPDATE_RESULT}; then
        rm -f "${SOURCE_FILE_PATH}" "${KEY_FILE_PATH}"
        return ${APT_UPDATE_RESULT}
    fi
    return 0
}

# https://dev.to/henrybarreto/pacman-s-simple-guide-for-apt-s-users-5hc4



function pacman_update_and_upgrade() {
    pacman -Syu || return $?
    return 0
}

function pacman_install_packages() {
    pacman -S ${1} || return $?
    return 0
}

function pacman_is_package_installed() {
    pacman -Q "${1}"
    return $?
}

function package_manager_update_and_upgrade() {
    if package_manager_is_apt; then
        apt_update_and_upgrade || return $?
    elif package_manager_is_pacman; then
        pacman_update_and_upgrade || return $?
    elif package_manager_is_yum; then
        # fixme utopia Дописать
        return 1
    elif package_manager_is_dnf; then
        # fixme utopia Дописать
        return 1
    elif package_manager_is_zypper; then
        # fixme utopia Дописать
        return 1
    else
        echo "FATAL: unknown package manager"
        return 1
    fi
    return 0
}

function package_manager_install_packages() {
    local PACKAGE_LIST="${1}"

    if package_manager_is_apt; then
        apt_install_packages "${PACKAGE_LIST}" || return $?
    elif package_manager_is_pacman; then
        pacman_install_packages "${PACKAGE_LIST}" || return $?
    elif package_manager_is_yum; then
        # fixme utopia Дописать
        return 1
    elif package_manager_is_dnf; then
        # fixme utopia Дописать
        return 1
    elif package_manager_is_zypper; then
        # fixme utopia Дописать
        return 1
    else
        echo "FATAL: unknown package manager"
        return 1
    fi
    return 0
}

function package_manager_is_package_installed() {
    local PACKAGE="${1}"

    if package_manager_is_apt; then
        apt_is_package_installed "${PACKAGE}"
        return $?
    elif package_manager_is_pacman; then
        pacman_is_package_installed "${PACKAGE}"
        return $?
    elif package_manager_is_yum; then
        # fixme utopia Дописать
        return 1
    elif package_manager_is_dnf; then
        # fixme utopia Дописать
        return 1
    elif package_manager_is_zypper; then
        # fixme utopia Дописать
        return 1
    else
        echo "FATAL: unknown package manager"
        return 1
    fi
    return 0
}

### System package manager end

function pip_update() {
    if is_termux; then
        return 0
    fi
    python3 -m pip install pip --force-reinstall --ignore-installed || return $?
    return 0
}

function pip_install_packages() {
    for pip_package in ${1}; do
        pip3 install "${pip_package}" --force-reinstall --ignore-installed || return $?
    done
    return 0
}

### termux specific API begin

function termux_autorun_serves_at_boot() {
    local AUTORUN_SERVICES_DIR_PATH="$(user_get_home_directory_path)/.termux/boot"
    local AUTORUN_SERVICES_SCRIPT="autorun_services_at_boot.sh"

    local AUTORUN_SERVICES_SCRIPT_PATH="${AUTORUN_SERVICES_DIR_PATH}/${AUTORUN_SERVICES_SCRIPT}"

    create_file "#!${SHELL}
termux-wake-lock
. \"${GLOBAL_CONFIG_ETC_PREFIX}/profile\"" "${AUTORUN_SERVICES_SCRIPT_PATH}" "rewrite_if_exist" || return $?
    set_file_as_executable "${AUTORUN_SERVICES_SCRIPT_PATH}" || return $?
    return 0
}

# https://wiki.termux.com/wiki/Internal_and_external_storage
# https://stackoverflow.com/questions/29789204/bash-how-to-get-real-path-of-a-symlink
function termux_set_symlinks_to_storage() {
   local TARGET_DIRECTORY_PATH="${1}"
   if [[ -z "${TARGET_DIRECTORY_PATH}" ]]; then
       TARGET_DIRECTORY_PATH="."
   fi

   # Вылезет запрос доступа к накопителю (Android).
   # Как только будет получено разрешение, в домашней директории появится директория storage
   termux-setup-storage || return $?
   local TERMUX_STORAGE_SYMLINKS_DIR_PATH="$(user_get_home_directory_path)/storage"
   wait_for_dir_creation "${TERMUX_STORAGE_SYMLINKS_DIR_PATH}" || return $?

   local ANDROID_INTERNAL_STORAGE_DIR_PATH="${TERMUX_STORAGE_SYMLINKS_DIR_PATH}/shared"
   if wait_for_dir_creation "${ANDROID_INTERNAL_STORAGE_DIR_PATH}"; then
       ANDROID_INTERNAL_STORAGE_DIR_PATH=$(realpath "${ANDROID_INTERNAL_STORAGE_DIR_PATH}") || return $?
       if [[ -d "${ANDROID_INTERNAL_STORAGE_DIR_PATH}" ]]; then
           create_symlink "${ANDROID_INTERNAL_STORAGE_DIR_PATH}" "${TARGET_DIRECTORY_PATH}/android-internal-storage" || return $?
       fi
   fi

   # external-1 -> /storage/9C33-6BBD/Android/data/com.termux/files
   # В итоге хотим получить /storage/9C33-6BBD
   sleep 1
   local ANDROID_EXTERNAL_STORAGE_DIR_PATH="${TERMUX_STORAGE_SYMLINKS_DIR_PATH}/external-1"
   if [[ -d "${ANDROID_EXTERNAL_STORAGE_DIR_PATH}" ]]; then
       ANDROID_EXTERNAL_STORAGE_DIR_PATH=$(realpath "${ANDROID_EXTERNAL_STORAGE_DIR_PATH}") || return $?
       ANDROID_EXTERNAL_STORAGE_DIR_PATH=$(realpath "${ANDROID_EXTERNAL_STORAGE_DIR_PATH}/../../../../") || return $?
       if [[ -d "${ANDROID_EXTERNAL_STORAGE_DIR_PATH}" ]]; then
           create_symlink "${ANDROID_EXTERNAL_STORAGE_DIR_PATH}" "${TARGET_DIRECTORY_PATH}/android-external-storage" || return $?
       fi
   fi

   return 0
}

### termux specific API end

### System services begin

function systemd_get_base_dir_path() {
   echo "${GLOBAL_CONFIG_ETC_PREFIX}/systemd/system"
   return 0
}

function systemd_init() {
    return 0
}

function systemd_is_service_active() {
    local SERVICE_NAME="${1}"

    local SERVICE_STATUS=""
    SERVICE_STATUS=$(systemctl is-active "${SERVICE_NAME}" 2> "/dev/null") || return $?

    if [[ "${SERVICE_STATUS,,}" == "active" ]]; then
        return 0
    fi
    return 1
}

function systemd_service_enable() {
    local SERVICE_NAME="${1}"

    systemctl enable "${SERVICE_NAME}" > "/dev/null" || return $?
    systemctl start "${SERVICE_NAME}" > "/dev/null" || return $?
    return 0
}

function systemd_service_disable() {
    local SERVICE_NAME="${1}"

    systemctl stop "${SERVICE_NAME}" > "/dev/null" || return $?
    systemctl disable "${SERVICE_NAME}" > "/dev/null" || return $?
    return 0
}

function runit_is_service_active() {
    local SERVICE_NAME="${1}"

    # https://manpages.ubuntu.com/manpages/trusty/en/man8/sv.8.html
    local SERVICE_STATUS=""
    SERVICE_STATUS=$(sv -w 5 status "${SERVICE_NAME}" 2> "/dev/null") || return $?

    if [[ "${SERVICE_STATUS,,}" == "run: "* ]]; then # https://stackoverflow.com/a/229606
        return 0
    fi
    return 1
}


function runit_get_base_dir_path() {
    echo "${SVDIR}"
    return 0
}

# https://wiki.termux.com/wiki/Termux-services
# https://smarden.org/runit/
# https://wiki.termux.com/wiki/Termux:Boot

function runit_init() {
    if is_termux; then
        # Если не удалось запустить service-daemon то перезагружаем bash и запускаем скрипт setup-packages.sh вновь.
        # После установки termux-services рекомендовано перезапустить termux чтобы bash подхватил новые переменные окружения (нас интересует SVDIR)
        # https://github.com/termux/termux-services/tree/master
        # "Restart your shell so that the service-daemon is started"

        if [[ -z "$(runit_get_base_dir_path)" ]]; then # После установки пакета termux-services в /etc/profile.d/ добавляется скрипт start-services.sh
                                     # который устанавливает требуемые переменные окружения. Перезагрузим (команда exec) bash с полной
                                     # инициализацией и запустим текущий скрипт заново
            echo "RESTART BASH"
            exec ${SHELL} --login -c "${0}" # fixme utopia Надо расследовать циклические перезагрузки скрипта на Android/termux
            # После exec ${SHELL} управление не возвращается
            echo "NEVER"
        fi
        termux_autorun_serves_at_boot || return $?
        return 0
    fi
    return 0
}

function runit_service_enable() {
    local SERVICE_NAME="${1}"

    sv-enable "${SERVICE_NAME}" > "/dev/null"
    if ! check_result_code $?; then
        sleep 5
        sv-enable "${SERVICE_NAME}" > "/dev/null"
        if ! check_result_code $?; then
            # Иногда почему-то случается вылет runit и далее служба не может запуститься,
            # поэтому запустим runit заново
            . "${GLOBAL_CONFIG_ETC_PREFIX}/profile.d/start-services.sh" > "/dev/null" || return $?
            sleep 5
            sv-enable "${SERVICE_NAME}" > "/dev/null" || return $?
        fi
    fi
    return 0
}

function runit_service_disable() {
    local SERVICE_NAME="${1}"

    sv-disable "${SERVICE_NAME}" > "/dev/null" || return $?
    return 0
}

# https://wiki.termux.com/wiki/Termux-services
function runit_create_log_run_file() {
    local SERVICE_NAME="${1}"

    local RUN_FILE_DIRECTOR_PATH="$(runit_get_base_dir_path)/${SERVICE_NAME}/log"
    local RUN_FILE_PATH="${RUN_FILE_DIRECTOR_PATH}/run"

    make_dirs "${RUN_FILE_DIRECTOR_PATH}" || return $?

    create_symlink "${PREFIX}/share/termux-services/svlogger" "${RUN_FILE_PATH}" || return $?
    return 0
}

function runit_create_run_file() {
    local SERVICE_NAME="${1}"
    local RUN_FILE_CONTENT="${2}"
    local FINISH_FILE_CONTENT="${3}"

    local RUN_FILE_DIRECTOR_PATH="$(runit_get_base_dir_path)/${SERVICE_NAME}"
    local RUN_FILE_PATH="${RUN_FILE_DIRECTOR_PATH}/run"
    local FINISH_FILE_PATH="${RUN_FILE_DIRECTOR_PATH}/finish"

    make_dirs "${RUN_FILE_DIRECTOR_PATH}" || return $?

    create_file "${RUN_FILE_CONTENT}" "${RUN_FILE_PATH}" || return $?
    set_file_as_executable "${RUN_FILE_PATH}" || return $?

    if [[ -n "${FINISH_FILE_CONTENT}" ]]; then
        create_file "${FINISH_FILE_CONTENT}" "${FINISH_FILE_PATH}" || return $?
        set_file_as_executable "${FINISH_FILE_PATH}" || return $?
    fi

    runit_create_log_run_file "${SERVICE_NAME}" || return $?
    return 0
}

function service_init() {
    if is_termux; then
        runit_init || return $?
        return 0
    fi

    systemd_init || return $?
    return 0
}

function is_service_active() {
    local SERVICE_NAME="${1}"

    if is_termux; then
        runit_is_service_active "${SERVICE_NAME}" || return $?
        return 0
    fi

    systemd_is_service_active "${SERVICE_NAME}" || return $?
    return 0
}

function service_enable() {
    local SERVICE_NAME="${1}"

    if is_termux; then
        runit_service_enable "${SERVICE_NAME}" || return $?
        return 0
    fi

    systemd_service_enable "${SERVICE_NAME}" || return $?
    return 0
}

function service_disable() {
    local SERVICE_NAME="${1}"

    if is_termux; then
        runit_service_disable "${SERVICE_NAME}" || return $?
        return 0
    fi

    systemd_service_disable "${SERVICE_NAME}" || return $?
    return 0
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



# fixme utopia Добавим поддержку "X11Forwarding yes" в "$PREFIX/etc/ssh/sshd_config" (termux)
# https://www.reddit.com/r/termux/comments/bd5kz4/x_windows_remote_display/
function sshd_setup() {
    local SSHD="ssh" # https://tokmakov.msk.ru/blog/item/441

    if is_termux; then
        SSHD="sshd"
    fi

    service_disable "${SSHD}"

    user_create_password_if || return $?

    service_enable "${SSHD}" || return $?

    if ! is_service_active "${SSHD}"; then
        echo "FATAL: ${SSHD} not started"
        return 1
    fi
    return 0
}

function pycharm_install() {
    local PYCHARM="pycharm-community-2024.1.4"
    local DOWNLOAD_URL="https://download.jetbrains.com/python/${PYCHARM}.tar.gz"
    local INSTALL_DIRECTORY="${GLOBAL_CONFIG_ROOT_PREFIX}/opt"
    local PYCHARM_INSTALL_DIRECTORY="${INSTALL_DIRECTORY}/${PYCHARM}"

    if [[ -d "${PYCHARM_INSTALL_DIRECTORY}" ]]; then
        echo "WARNING: Pycharm \"${PYCHARM}\" already installed"
        return 0
    fi

    make_dirs "${INSTALL_DIRECTORY}" || return $?

    download_file "${DOWNLOAD_URL}" "-" | tar -xz -C "${INSTALL_DIRECTORY}" || return $?
    return 0
}

function rdp_client_install_default() {
    local RDP_CLIENT_PACKAGE="freerdp2-x11 freerdp2-wayland"
    if is_termux; then
        RDP_CLIENT_PACKAGE="freerdp"
    fi

    package_manager_install_packages "${RDP_CLIENT_PACKAGE}" || return $?
    return 0
}

function rdp_client_install_nightly() {
    if package_manager_is_apt; then
        local OS_DISTRO_VERSION_CODENAME=""
        OS_DISTRO_VERSION_CODENAME=$(get_os_distro_codename_or_version) || return $?

        local PACKAGE_NAME="freerdp-nightly"
        local KEY_FILE_URL="http://pub.freerdp.com/repositories/ADD6BF6D97CE5D8D.asc"
        local URIS="http://pub.freerdp.com/repositories/deb/${OS_DISTRO_VERSION_CODENAME}"
        local SUITES="${PACKAGE_NAME}"
        local COMPONENTS="main"
        local ARCHITECTURES="amd64"
        apt_add_sources "${PACKAGE_NAME}" "${KEY_FILE_URL}" "${URIS}" "${SUITES}" "${COMPONENTS}" "${ARCHITECTURES}" || return $?
        package_manager_install_packages "${PACKAGE_NAME}" || return $?
        echo "PACKAGE INSTALLED: \"${PACKAGE_NAME}\", run /opt/freerdp-nightly/bin/xfreerdp"
        return 0
    fi
    return 1
}

function rdp_client_install() {
    if is_termux; then
        rdp_client_install_default || return $?
    else
        rdp_client_install_nightly || rdp_client_install_default || return $? # fixme utopia Чтобы будем делать с Linux ARM?
    fi

    # https://interface31.ru/tech_it/2022/09/apt-key-is-deprecated-ili-upravlenie-klyuchami-v-sovremennyh-vypuskah-debian-i-ubunt.html
    # https://habr.com/en/articles/683716/
    return 0
}

function winetricks_install_default() {
   local DOWNLOAD_URL="https://github.com/Winetricks/winetricks/archive/refs/tags/20240105.tar.gz"
   local INSTALL_DIRECTORY="${GLOBAL_CONFIG_ROOT_PREFIX}/opt/winetricks"

   rm -rf "${INSTALL_DIRECTORY}" || return $?
   make_dirs "${INSTALL_DIRECTORY}" || return $?

   download_file "${DOWNLOAD_URL}" "-" | tar -xz -C "${INSTALL_DIRECTORY}" --strip-components=1 || return $?
   make -C "${INSTALL_DIRECTORY}" DESTDIR="${GLOBAL_CONFIG_ROOT_PREFIX}" install || return $?
   return 0
}

function wine_install_default() {
    if is_termux; then
        package_manager_install_packages "wine-stable" || return $?
        return 0
    fi

    package_manager_install_packages "wine" || return $?
    return 0
}

# https://wiki.winehq.org/Ubuntu
function wine_install_nightly() {
    if package_manager_is_apt; then
        local OS_DISTRO_VERSION_CODENAME=""
        OS_DISTRO_VERSION_CODENAME=$(get_os_distro_codename_or_version) || return $?

        local OS_DISTRO_NAME=""
        OS_DISTRO_NAME=$(get_os_distro_name) || return $?

        local NAME="winehq"
        local PACKAGE_NAME="${NAME}-stable"
        local KEY_FILE_URL="https://dl.winehq.org/wine-builds/winehq.key"
        local URIS="https://dl.winehq.org/wine-builds/${OS_DISTRO_NAME}"
        local SUITES="${OS_DISTRO_VERSION_CODENAME}"
        local COMPONENTS="main"
        local ARCHITECTURES="amd64 i386"
        apt_add_sources "${NAME}" "${KEY_FILE_URL}" "${URIS}" "${SUITES}" "${COMPONENTS}" "${ARCHITECTURES}" || return $?
        package_manager_install_packages "--install-recommends ${PACKAGE_NAME}" || return $?
        echo "PACKAGE INSTALLED: \"${PACKAGE_NAME}\""
        return 0
    fi
    return 1
}

function wine_install_32bit_dependencies() {
    # Зависимости для wine32 fixme utopia Это Ubuntu специфичные пакеты?
    # https://pkgs.org/search/?q=libgl1
    # https://pkgs.org/search/?q=mesa-vulkan-drivers
    package_manager_install_packages "libgl1:i386 mesa-vulkan-drivers:i386" || return $?
    return 0
}

function wine_install() {
    if is_termux; then
        # fixme utopia Будем устанавливать в termux для архитектуры amd64/i386? Проверить в termux
        # fixme utopia Запуск из под box86/box64
        # fixme utopia Запуск ARM программ под ARM/wine?
        # https://github.com/termux/termux-packages/blob/master/x11-packages/wine-stable/build.sh
        wine_install_default || return $?
    else
        wine_install_32bit_dependencies || return $?
        wine_install_nightly || wine_install_default || return $?
    fi

    winetricks_install_default || return $?

    # fixme utopia Install Mono and Gecko automatically
    # откуда версию Mono то взять? Курить внимательно appwiz.cpl
    # https://source.winehq.org/winemono.php?arch=x86_64&v=8.1.0&winev=8.19
    # https://gitlab.winehq.org/wine/wine/-/blob/master/dlls/appwiz.cpl/addons.c
    # https://www.winehq.org/pipermail/wine-bugs/2014-January/373915.html

    # https://gist.github.com/RobinCPC/9f42be23a1343600507aabdfecc5061d
    # https://wiki.winehq.org/Mono
    # https://wiki.winehq.org/Gecko
    # https://forum.winehq.org/viewtopic.php?t=37344
    # https://source.winehq.org/

    return 0
}

function smbd_get_config_file_path() {
    local SMBD_BUILD_OPTIONS
    SMBD_BUILD_OPTIONS=$(smbd -b) || return $?

    local SMBD_CONFIG_FILE_PATH
    SMBD_CONFIG_FILE_PATH=$(echo "${SMBD_BUILD_OPTIONS}" | sed -En 's/^[\t ]*CONFIGFILE:[\t ]+(.*)$/\1/p') || return $? # https://stackoverflow.com/a/43997253

    echo "${SMBD_CONFIG_FILE_PATH}"
    return 0
}

function samba_make_user_and_assign_rights() {
    if ! is_termux; then
        # https://askubuntu.com/questions/97669/i-cant-get-samba-to-set-proper-permissions-on-created-directories

        local SAMBA_USER="${1}"
        local SAMBASHARE_GROUP="sambashare"

        if ! user_is_available "${SAMBA_USER}"; then
            user_add "${SAMBA_USER}" || return $?
        fi

        if ! user_is_added_to_group "${SAMBA_USER}" "${SAMBASHARE_GROUP}"; then
            user_add_to_group "${SAMBA_USER}" "${SAMBASHARE_GROUP}" || return $?
        fi
        return 0
    fi
    return 0
}

function samba_make_public_directory() {
    make_dirs "${GLOBAL_CONFIG_SAMBA_PUBLIC_DIRECTORY_PATH}" || return $?
    chmod 0777 "${GLOBAL_CONFIG_SAMBA_PUBLIC_DIRECTORY_PATH}" || return $?
    return 0
}

function smbd_make_config() {
    # https://www.samba.org/samba/docs/current/man-html/smb.conf.5.html

    local SMBD_CONFIG_FILE_PATH
    SMBD_CONFIG_FILE_PATH=$(smbd_get_config_file_path) || return $?

    # fixme utopia Задать обнаружение NetBios
    # https://www.linux.org.ru/forum/admin/13225419
    # https://en.wikipedia.org/wiki/NetBIOS#NetBIOS_name
    # getprop ro.product.model
    # getprop ro.product.manufacturer

    # https://learn.microsoft.com/en-us/answers/questions/1280211/symbolic-links-created-by-linux-are-not-displayed
    # fixme utopia Переписать?
    # https://www.samba.org/samba/docs/using_samba/ch08.html#samba2-CHP-8-TABLE-2
    create_file "[global]
workgroup = WORKGROUP
security = user
map to guest = bad user
wins support = no
dns proxy = no
smb ports = ${GLOBAL_CONFIG_SMBD_TCP_PORTS}
inherit permissions = yes
follow symlinks = yes
wide links = yes
allow insecure wide links = yes

[public]
path = \"${GLOBAL_CONFIG_SAMBA_PUBLIC_DIRECTORY_PATH}\"
guest ok = yes
force user = ${GLOBAL_CONFIG_SAMBA_USER}
browsable = yes
writable = yes
" "${SMBD_CONFIG_FILE_PATH}" || return $?
    return 0
}

function smbd_setup() {
    # https://ubuntu.com/tutorials/install-and-configure-samba#1-overview
    local SMBD="smbd"

    service_disable "${SMBD}"

    # make_samba_user_and_assign_rights || return $?
    samba_make_public_directory || return $?
    smbd_make_config || return $?

    if is_termux; then
        local SMBD_EXECUTABLE_PATH=""
        SMBD_EXECUTABLE_PATH=$(which "${SMBD}") || return $?

        runit_create_run_file "${SMBD}" \
"#!${SHELL}
exec ${SMBD_EXECUTABLE_PATH} --foreground --no-process-group --debug-stdout --debuglevel=3 2>&1 || exit $?
exit 0" || return $?

        termux_set_symlinks_to_storage "${GLOBAL_CONFIG_SAMBA_PUBLIC_DIRECTORY_PATH}"
    fi

    service_enable "${SMBD}" || return $?

    if ! is_service_active "${SMBD}"; then
        echo "FATAL: ${SMBD} not started"
        return 1
    fi

    # https://www.samba.org/~tpot/articles/firewall.html
    # https://ixnfo.com/iptables-pravila-dlya-samba.html
    # https://unlix.ru/%D0%BD%D0%B0%D1%81%D1%82%D1%80%D0%BE%D0%B9%D0%BA%D0%B0-%D1%84%D0%B0%D0%B5%D1%80%D0%B2%D0%BE%D0%BB%D0%B0-iptables-%D0%B4%D0%BB%D1%8F-samba/
    # https://entnet.ru/server/domain/ustanovka-i-nastrojka-samba-server.html
    return 0
}

function desktop_environment_get_desktop_file_path() {
    local DESKTOP_ENVIRONMENT_PRIORITY_LIST="xfce cinnamon"
    local DESKTOP_ENVIRONMENT_DIR_PATH="${GLOBAL_CONFIG_USR_PREFIX}/share/xsessions"

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
    local XSTARTUP_FILE_PATH="${1}"

    local DESKTOP_ENVIRONMENT_DESKTOP_FILE_PATH=""
    DESKTOP_ENVIRONMENT_DESKTOP_FILE_PATH=$(desktop_environment_get_desktop_file_path) || return $?

    local EXEC=""
    EXEC=$(desktop_file_get_value "${DESKTOP_ENVIRONMENT_DESKTOP_FILE_PATH}" "Desktop Entry" "Exec") || return $?

    create_file "#!${SHELL}
autocutsel -fork
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
${EXEC}" "${XSTARTUP_FILE_PATH}" || return $?
    set_file_as_executable "${XSTARTUP_FILE_PATH}" || return $?
    return 0
}

function vnc_server_get_executable_path() {
    local VNC_SERVER_EXEC="vncserver"
    local RESULT=""
    RESULT=$(which "${VNC_SERVER_EXEC}") || return $?
    echo "${RESULT}"
    return 0
}

function vnc_server_get_config_info() {
    local -n RESULT_REF=${1}
    local VNC_USER="${2}"

    local INIT_SYSTEM_BASE_DIR_PATH=""
    local INIT_SYSTEM_BASE_DIR_PATH_FILTER_TYPE=""
    if is_termux; then
        INIT_SYSTEM_BASE_DIR_PATH="$(runit_get_base_dir_path)"
        INIT_SYSTEM_BASE_DIR_PATH_FILTER_TYPE="d"
    else
        INIT_SYSTEM_BASE_DIR_PATH="$(systemd_get_base_dir_path)"
        INIT_SYSTEM_BASE_DIR_PATH_FILTER_TYPE="f"
    fi

    local VNCD_BASENAME="vncd"
    local VNCD_INSTANCE_NAME_REGEX="${VNCD_BASENAME}@(.+)-([0-9]+).service$"

    local VNC_USER_HOME_DIRECTORY_PATH=""
    VNC_USER_HOME_DIRECTORY_PATH=$(user_get_home_directory_path "${VNC_USER}") || return $?
    local VNC_XSTARTUP_FILE_PATH="${VNC_USER_HOME_DIRECTORY_PATH}/.vnc/xstartup"

    local VNC_SERVER_EXECUTABLE_PATH=""
    VNC_SERVER_EXECUTABLE_PATH=$(vnc_server_get_executable_path) || return $?

    RESULT_REF["EXECUTABLE_PATH"]="${VNC_SERVER_EXECUTABLE_PATH}"
    RESULT_REF["USER"]="${VNC_USER}"
    RESULT_REF["USER_HOME_DIRECTORY_PATH"]="${VNC_USER_HOME_DIRECTORY_PATH}"
    RESULT_REF["XSTARTUP_FILE_PATH"]="${VNC_XSTARTUP_FILE_PATH}"

    local INIT_SYSTEM_CONFIG_PATH_LIST=()
    get_directory_paths INIT_SYSTEM_CONFIG_PATH_LIST "${INIT_SYSTEM_BASE_DIR_PATH}" "${VNCD_BASENAME}@*.service" "${INIT_SYSTEM_BASE_DIR_PATH_FILTER_TYPE}" || return $?

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

    local VNC_SERVER_EXECUTABLE_PATH="${VNC_SERVER_CONFIG_REF["EXECUTABLE_PATH"]}"
    local VNC_USER="${VNC_SERVER_CONFIG_REF["USER"]}"
    local VNC_USER_HOME_DIRECTORY_PATH="${VNC_SERVER_CONFIG_REF["USER_HOME_DIRECTORY_PATH"]}"
    local VNC_DISPLAY=":${VNC_SERVER_CONFIG_REF["DISPLAY_NUMBER"]}"
    local VNCD_INSTANCE_CONFIG_PATH="${VNC_SERVER_CONFIG_REF["INSTANCE_CONFIG_PATH"]}"


    # https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html#Options
    # https://www.digitalocean.com/community/tutorials/how-to-install-and-configure-vnc-on-ubuntu-22-04
    # https://wiki.archlinux.org/title/Systemd_(%D0%A0%D1%83%D1%81%D1%81%D0%BA%D0%B8%D0%B9)#%D0%A2%D0%B8%D0%BF%D1%8B_%D1%81%D0%BB%D1%83%D0%B6%D0%B1
    create_file "[Unit]
Description=Start VNC server at startup
After=syslog.target network.target

[Service]
Type=forking
User=${VNC_USER}
Group=${VNC_USER}
WorkingDirectory=${VNC_USER_HOME_DIRECTORY_PATH}

ExecStartPre=-${VNC_SERVER_EXECUTABLE_PATH} -kill ${VNC_DISPLAY} > /dev/null 2>&1
ExecStart=${VNC_SERVER_EXECUTABLE_PATH} -localhost no ${VNC_DISPLAY}
ExecStop=${VNC_SERVER_EXECUTABLE_PATH} -kill ${VNC_DISPLAY}

[Install]
WantedBy=multi-user.target" "${VNCD_INSTANCE_CONFIG_PATH}" || return $?
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
    local VNC_USER_HOME_DIRECTORY_PATH="${1}"

    if [[ ! -f "${VNC_USER_HOME_DIRECTORY_PATH}/.vnc/passwd" ]]; then
        echo "Set VNC password"
        vncpasswd || return $?
        return 0
    fi

    return 0
}

function vnc_server_setup() {
    local declare -A VNC_SERVER_CONFIG=()
    vnc_server_get_config_info VNC_SERVER_CONFIG "${GLOBAL_CONFIG_VNC_USER}" || return $?

    local VNCD_INSTANCE_NAME="${VNC_SERVER_CONFIG["INSTANCE_NAME"]}"
    local VNC_XSTARTUP_FILE_PATH="${VNC_SERVER_CONFIG["XSTARTUP_FILE_PATH"]}"
    local VNC_USER_HOME_DIRECTORY_PATH="${VNC_SERVER_CONFIG["USER_HOME_DIRECTORY_PATH"]}"

    service_disable "${VNCD_INSTANCE_NAME}"

    vnc_server_create_xstartup "${VNC_XSTARTUP_FILE_PATH}" || return $?

    if is_termux; then
        vnc_server_create_runit_config VNC_SERVER_CONFIG || return $?
    else
        vnc_server_create_systemd_config VNC_SERVER_CONFIG || return $?
    fi

    vnc_create_password_if "${VNC_USER_HOME_DIRECTORY_PATH}" || return $?

    service_enable "${VNCD_INSTANCE_NAME}" || return $?

    if ! is_service_active "${VNCD_INSTANCE_NAME}"; then
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

# https://openvpn.net/cloud-docs/owner/connectors/connector-user-guides/openvpn-3-client-for-linux.html
function openvpn3_setup() {
    if is_termux; then
        return 0
    fi

    if package_manager_is_apt; then
        local OS_DISTRO_VERSION_CODENAME=""
        OS_DISTRO_VERSION_CODENAME=$(get_os_distro_codename_or_version) || return $?

        local PACKAGE_NAME="openvpn3"
        local KEY_FILE_URL="https://packages.openvpn.net/packages-repo.gpg"
        local URIS="https://packages.openvpn.net/openvpn3/debian"
        local SUITES="${OS_DISTRO_VERSION_CODENAME}"
        local COMPONENTS="main"
        local ARCHITECTURES="amd64"
        apt_add_sources "${PACKAGE_NAME}" "${KEY_FILE_URL}" "${URIS}" "${SUITES}" "${COMPONENTS}" "${ARCHITECTURES}" || return $?
        package_manager_install_packages "${PACKAGE_NAME}" || return $?
        echo "PACKAGE INSTALLED: \"${PACKAGE_NAME}\", run ${PACKAGE_NAME}"
        return 0
    fi
    return 1
}

# https://docs.waydro.id/usage/install-on-desktops#ubuntu-debian-and-derivatives
# https://repo.waydro.id/
function waydroid_setup() {
    if is_termux; then
        return 0
    fi

    if package_manager_is_apt; then
        local OS_DISTRO_VERSION_CODENAME=""
        OS_DISTRO_VERSION_CODENAME=$(get_os_distro_codename_or_version) || return $?

        local PACKAGE_NAME="waydroid"
        local KEY_FILE_URL="https://repo.waydro.id/waydroid.gpg"
        local URIS="https://repo.waydro.id"
        local SUITES="${OS_DISTRO_VERSION_CODENAME}"
        local COMPONENTS="main"
        local ARCHITECTURES="amd64"
        apt_add_sources "${PACKAGE_NAME}" "${KEY_FILE_URL}" "${URIS}" "${SUITES}" "${COMPONENTS}" "${ARCHITECTURES}" || return $?
        package_manager_install_packages "${PACKAGE_NAME}" || return $?
        echo "PACKAGE INSTALLED: \"${PACKAGE_NAME}\", run ${PACKAGE_NAME}"
        return 0
    fi
    return 1
}

function main_install_min_packages() {
    local PACKAGE_LIST="${1}"

    package_manager_update_and_upgrade || return $?

    package_manager_install_packages "${PACKAGE_LIST}" || return $?
    service_init || return $?
    pip_update || return $?
    pip_install_packages "${PIP_PACKAGES}" || return $?
    return 0
}

function main_install_dev_packages() {
    local PACKAGE_LIST="${1}"

    main_install_min_packages "${PACKAGE_LIST}" || return $?

    rdp_client_install || return $?
    sshd_setup || return $?
    vnc_server_setup || return $?
    smbd_setup || return $?
    return 0
}

function main_install_full_packages() {
    local PACKAGE_LIST="${1}"

    main_install_dev_packages "${PACKAGE_LIST}" || return $?

    pycharm_install || return $?
    wine_install || return $?
    openvpn3_setup || return $?
    waydroid_setup || return $?
    return 0
}

function main() {
    package_manager_update_and_upgrade || return $?

    if [[ "${GLOBAL_CONFIG_SETUP_PACKAGES_MODE,,}" == "min" ]]; then
        main_install_min_packages "${MINIMAL_PACKAGES}" || return $?
    elif [[ "${GLOBAL_CONFIG_SETUP_PACKAGES_MODE,,}" == "dev" ]]; then
        main_install_dev_packages "${DEV_PACKAGES}" || return $?
    else
        main_install_full_packages "${FULL_PACKAGES}" || return $?
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