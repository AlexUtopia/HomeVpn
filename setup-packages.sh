#!/bin/bash

#set -x # Раскомментировать для отладки

PYTHON_VERSION_MIN="3.8"

PYTHON_VERSION="3.10"

function is_termux() {
    if [[ -z "${TERMUX_VERSION}" ]]; then
        return 1
    fi
    return 0
}

# fixme utopia Проверка минимальной версии питона


RUN_WITH_ADMIN_RIGHTS="sudo"
if is_termux; then
    RUN_WITH_ADMIN_RIGHTS=""
fi

### Minimal packages begin

OPEN_VPN_PACKAGE="openvpn"
WGET_PACKAGE="wget"
TAR_PACKAGE="tar"
PROCPS_PACKAGE="procps" # Утилита sysctl для записи параметров ядра linux
IPTABLES_PACKAGE="iptables" # Настройки фaйервола
IPROUTE2_PACKAGE="iproute2" # Утилита ip управления сетевыми интерфейсами
COREUTILS_PACKAGE="coreutils" # Утилита uname

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
VNC_SERVER_PACKAGE="tightvncserver"
if is_termux; then
    VNC_SERVER_PACKAGE="tigervnc"
fi

AUXILIARY_UTILITIES="cpu-checker util-linux pciutils usbutils lshw" # Утилиты kvm-ok, lscpu, lspci, lsusb, lshw
if is_termux; then
    AUXILIARY_UTILITIES="util-linux pciutils"
fi

TELNET_CLIENT_PACKAGE="putty" # Для подключения к qemu monitor

SAMBA_PACKAGE="samba"

SYSTEMD_PACKAGE="systemd" # Утилита systemctl
if is_termux; then
    SYSTEMD_PACKAGE=""
fi

DEV_PACKAGES="${MINIMAL_PACKAGES} ${GIT_PACKAGE} ${AUTOCUTSEL_PACKAGE} ${NANO_PACKAGE} ${SSH_SERVER_PACKAGE} ${VNC_CLIENT_PACKAGE} ${VNC_SERVER_PACKAGE} ${AUXILIARY_UTILITIES} ${TELNET_CLIENT_PACKAGE} ${SAMBA_PACKAGE} ${SYSTEMD_PACKAGE}"
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

FULL_PACKAGES="${DEV_PACKAGES} ${DOUBLE_COMMANDER_PACKAGE} ${MIDNIGHT_COMMANDER_PACKAGE} ${XFCE4_PACKAGE} ${FIREFOX_PACKAGE} ${OPEN_JDK_PACKAGE} ${QT_CREATOR_PACKAGE}"
### Full packages end


PIP_PACKAGES="pystun3==1.0.0 python-iptables==1.0.0 psutil==5.9.1 netaddr==0.8.0 randmac==0.1 transmission-rpc==4.2.0 semantic_version==2.10.0 os-release==1.0.1"


function get_system_name() {
    SYSTEM_NAME=`uname -o`
    echo "${SYSTEM_NAME,,}"
}

function install_packages() {
    ${RUN_WITH_ADMIN_RIGHTS} apt install ${1} -y || return $?
    return 0
}

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

function setup_sshd() {
    local SSHD_IS_RUNNING=$(systemctl is-active sshd)

    if [ "${SSHD_IS_RUNNING,,}" = "active" ]; then
      return 0
    fi
    ${RUN_WITH_ADMIN_RIGHTS} systemctl enable sshd || return $?
    return 0
}

function install_pycharm() {
    # https://www.jetbrains.com/edu-products/download/other-PCE.html
    # Текущая версия 2023.2.3 (Community Edition)
    # fixme utopia Реализовать
    return 0
}

function install_rdp_client() {
    # https://pub.freerdp.com/releases/
    # https://github.com/FreeRDP/FreeRDP
    # fixme utopia Реализовать
    # echo "FreeRDP installed to <directory>, see https://github.com/FreeRDP/FreeRDP/wiki/CommandLineInterface"
    return 0
}

function setup_smbd() {
    # fixme utopia Реализовать, см. пример конфига в телеграмме
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

install_packages "${DEV_PACKAGES}" || exit $?

update_pip || exit $?

install_pip_packages "${PIP_PACKAGES}" || exit $?

install_rdp_client || exit $?

install_pycharm || exit $?

setup_sshd || exit $?

setup_smbd || exit $?

setup_vnc_server || exit $?
