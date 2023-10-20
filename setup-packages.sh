#!/bin/bash

PYTHON_VERSION_MIN="3.8"

PYTHON_VERSION="3.10"

# fixme utopia Выделить минимально необходимый набор пакетов для запуска системы, набор пакетов разработчика и полный
# fixme utopia Проверка минимальной версии питона
# fixme utopia Настройка VNC сервера + демонизация (для linux и termux)

GIT_PACKAGE="git"
OPEN_VPN_PACKAGE="openvpn"
WGET_PACKAGE="wget"
TAR_PACKAGE="tar"
VNC_CLIENT_PACKAGE="tigervnc-viewer"
PROCPS_PACKAGE="procps" # Утилита sysctl для записи параметров ядра linux
IPTABLES_PACKAGE="iptables" # Настройки фaйервола
IPROUTE2_PACKAGE="iproute2" # Утилита ip управления сетевыми интерфейсами
COREUTILS_PACKAGE="coreutils" # Утилита uname
AUTOCUTSEL_PACKAGE="autocutsel" # Используется для организации буфера обмена для VNC сессии, см. https://superuser.com/a/1524282

#libvirglrenderer1

LINUX_PYTHON3_PACKAGE="python3"
LINUX_PYTHON3_PIP_PACKAGE="python3-pip"
LINUX_PYTHON3_VENV_PACKAGE="python3-venv"
LINUX_SSH_CLIENT_PACKAGE="ssh"
LINUX_SSH_SERVER_PACKAGE="openssh-server"
LINUX_VNC_SERVER_PACKAGE="tightvncserver"
LINUX_DNSMASQ_PACKAGE="dnsmasq-base" # DNS/DHCP сервер для сетевых адаптеров виртуальных машин qemu
LINUX_QEMU_SYSTEM_PACKAGE="qemu qemu-system qemu-kvm"
LINUX_AUXILIARY_UTILITIES="cpu-checker util-linux pciutils usbutils lshw" # Утилиты kvm-ok, lscpu, lspci, lsusb, lshw
LINUX_SYSTEMD_PACKAGE="systemd" # Утилита systemctl

TERMUX_PYTHON3_PACKAGE="python"
TERMUX_PYTHON3_PIP_PACKAGE="python-pip"
TERMUX_PYTHON3_VENV_PACKAGE=""
TERMUX_SSH_CLIENT_PACKAGE="openssh"
TERMUX_SSH_SERVER_PACKAGE=""
TERMUX_VNC_SERVER_PACKAGE="tigervnc"
TERMUX_DNSMASQ_PACKAGE=""
TERMUX_QEMU_SYSTEM_PACKAGE="qemu-system-x86-64"
TERMUX_AUXILIARY_UTILITIES="util-linux pciutils" # Утилиты lscpu, lspci

#virglrenderer / virglrenderer-android

PIP_PACKAGES="pystun3==1.0.0 python-iptables==1.0.0 psutil==5.9.1 netaddr==0.8.0 randmac==0.1 transmission-rpc==4.2.0 semantic_version==2.10.0 os-release==1.0.1"


COMMON_PACKAGES="${GIT_PACKAGE} ${OPEN_VPN_PACKAGE} ${WGET_PACKAGE} ${TAR_PACKAGE} ${VNC_CLIENT_PACKAGE} ${PROCPS_PACKAGE} ${IPTABLES_PACKAGE} ${IPROUTE2_PACKAGE} ${COREUTILS_PACKAGE} ${AUTOCUTSEL_PACKAGE}"

LINUX_SPECIFIC_PACKAGES="${LINUX_PYTHON3_PACKAGE} ${LINUX_PYTHON3_PIP_PACKAGE} ${LINUX_PYTHON3_VENV_PACKAGE} ${LINUX_SSH_CLIENT_PACKAGE} ${LINUX_SSH_SERVER_PACKAGE} ${LINUX_VNC_SERVER_PACKAGE} ${LINUX_DNSMASQ_PACKAGE} ${LINUX_QEMU_SYSTEM_PACKAGE} ${LINUX_AUXILIARY_UTILITIES}"

TERMUX_SPECIFIC_PACKAGES="${TERMUX_PYTHON3_PACKAGE} ${TERMUX_PYTHON3_PIP_PACKAGE} ${TERMUX_PYTHON3_VENV_PACKAGE} ${TERMUX_SSH_CLIENT_PACKAGE} ${TERMUX_SSH_SERVER_PACKAGE} ${TERMUX_VNC_SERVER_PACKAGE} ${TERMUX_DNSMASQ_PACKAGE} ${TERMUX_QEMU_SYSTEM_PACKAGE} ${TERMUX_AUXILIARY_UTILITIES}"


function get_system_name() {
    echo `uname -o`
}

function install_packages() {
    local SYSTEM_NAME=$(get_system_name)
    if [ "${SYSTEM_NAME,,}" = "android" ]; then
        sudo apt install ${COMMON_PACKAGES} ${TERMUX_SPECIFIC_PACKAGES} -y || return $?
    else
        sudo apt install ${COMMON_PACKAGES} ${LINUX_SPECIFIC_PACKAGES} -y || return $?
    fi
    return 0
}

function update_pip() {
    sudo python3 -m pip install pip --force-reinstall --ignore-installed || return $?
    return 0
}

function install_pip_packages() {
    for pip_package in ${1}
    do
      sudo pip3 install "${pip_package}" --force-reinstall --ignore-installed || return $?
    done
    return 0
}

function setup_sshd() {
    local SSHD_IS_RUNNING=$(systemctl is-active sshd)

    if [ "${SSHD_IS_RUNNING,,}" = "active" ]; then
      return 0
    fi
    sudo systemctl enable sshd || return $?
    return 0
}

install_packages || exit $?

update_pip || exit $?

install_pip_packages "${PIP_PACKAGES}" || exit $?

setup_sshd || exit $?
