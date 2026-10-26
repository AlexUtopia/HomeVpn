#!/bin/bash

# @file project.default.config.sh
# @brief Настройки экземпляра проекта
# @description
# python скрипт получит конфигурацию из переменных окружения.
#
#          Путь до скрипта с настройками текущего экземпляра проекта:
#              os.environ['CONFIG_PROJECT_INSTANCE_FILE_PATH']
#
#          Настройки текущего экземпляра проекта (примеры):
#              os.environ['CONFIG_OPENVPN_SERVER_PORT'] # Порт openvpn сервера
#              os.environ['CONFIG_DNS_MY_HOST']         # Доменное имя хоста виртуальной машины


# @set CONFIG_PROJECT_INSTANCE string Имя экземпляра проекта
export CONFIG_PROJECT_INSTANCE="HomeVpn"

# @set CONFIG_OPENVPN_SERVER_PORT int Порт openvpn сервера (в рамках экземпляра проекта)
export CONFIG_OPENVPN_SERVER_PORT=35000

# @set CONFIG_OPENVPN_DATA_DIR_PATH string Путь до директории данных экземпляра проекта
export CONFIG_OPENVPN_DATA_DIR_PATH="${GLOBAL_CONFIG_OPT_DIR_PATH}/${CONFIG_PROJECT_INSTANCE}"

# @set CONFIG_OPENVPN_SERVER_DATA_DIR_PATH string Путь до директории данных openvpn сервера (в рамках экземпляра проекта)
export CONFIG_OPENVPN_SERVER_DATA_DIR_PATH="${CONFIG_OPENVPN_DATA_DIR_PATH}/server"

# @set CONFIG_OPENVPN_SERVER_LOG_DIR_PATH string Путь до директории с логами openvpn сервера (в рамках экземпляра проекта)
export CONFIG_OPENVPN_SERVER_LOG_DIR_PATH="${CONFIG_OPENVPN_SERVER_DATA_DIR_PATH}/logs"

# @set CONFIG_OPENVPN_SERVER_CONFIG_FILE_PATH string Путь до файла конфигурации (.ovpn) openvpn сервера (в рамках экземпляра проекта)
export CONFIG_OPENVPN_SERVER_CONFIG_FILE_PATH="${CONFIG_OPENVPN_SERVER_DATA_DIR_PATH}/server.ovpn"

# @set CONFIG_EASYRSA_PKI_DIR_PATH string Путь до директории с сертификатами (EasyRSA) openvpn сервера/клиента (в рамках экземпляра проекта)
export CONFIG_EASYRSA_PKI_DIR_PATH="${CONFIG_OPENVPN_SERVER_DATA_DIR_PATH}/pki"

# @set CONFIG_OPENVPN_CLIENT_DATA_DIR_PATH_TEMPLATE string Шаблон пути до директории данных openvpn клиента (в рамках экземпляра проекта). %s заменяется на имя клиента
export CONFIG_OPENVPN_CLIENT_DATA_DIR_PATH_TEMPLATE="${CONFIG_OPENVPN_DATA_DIR_PATH}/client/%s"

# @set CONFIG_OPENVPN_CLIENT_LOG_DIR_PATH_TEMPLATE string Шаблон пути до директории с логами openvpn клиента (в рамках экземпляра проекта). %s заменяется на имя клиента
export CONFIG_OPENVPN_CLIENT_LOG_DIR_PATH_TEMPLATE="${CONFIG_OPENVPN_CLIENT_DATA_DIR_PATH_TEMPLATE}/logs"

# @set CONFIG_OPENVPN_CLIENT_CONFIG_FILE_PATH_TEMPLATE string Шаблон пути до файла конфигурации (.ovpn) openvpn клиента (в рамках экземпляра проекта). %s заменяется на имя клиента
export CONFIG_OPENVPN_CLIENT_CONFIG_FILE_PATH_TEMPLATE="${CONFIG_OPENVPN_CLIENT_DATA_DIR_PATH_TEMPLATE}/client.ovpn"

# @set CONFIG_MY_CURRENT_IP_ADDRESS_AND_PORT_FILE_PATH string Путь до файла куда записываются текущий публичный адрес и порт (в рамках экземпляра проекта)
export CONFIG_MY_CURRENT_IP_ADDRESS_AND_PORT_FILE_PATH="${CONFIG_OPENVPN_SERVER_DATA_DIR_PATH}/my_current_ip_address_and_port.txt"

# @set CONFIG_NETWORK_BRIDGE_IP_ADDRESS_AND_MASK string IP адрес и маска сетевого моста (в рамках экземпляра проекта)
export CONFIG_NETWORK_BRIDGE_IP_ADDRESS_AND_MASK="172.20.0.5/16"

# @set CONFIG_NETWORK_BRIDGE_DATA_DIR_PATH string Путь до директории данных сетевого моста (в рамках экземпляра проекта)
export CONFIG_NETWORK_BRIDGE_DATA_DIR_PATH="${CONFIG_OPENVPN_SERVER_DATA_DIR_PATH}/network_bridge"

# @set CONFIG_DNS_DHCP_DATA_DIR_PATH string Путь до директории данных DNS/DHCP сервера (в рамках экземпляра проекта)
export CONFIG_DNS_DHCP_DATA_DIR_PATH="${CONFIG_NETWORK_BRIDGE_DATA_DIR_PATH}/dns_dhcp"

# @set CONFIG_DNS_SUFFIX string DNS суффикс для виртуальных машин (в рамках экземпляра проекта)
export CONFIG_DNS_SUFFIX="${CONFIG_PROJECT_INSTANCE,,}.org"

# @set CONFIG_DNS_MY_HOST string Доменное имя хоста виртуальной машины (в рамках экземпляра проекта). Из виртуальной машины можно обратиться к её хосту по этому имени, а не по IP адресу
export CONFIG_DNS_MY_HOST="myhost.${CONFIG_DNS_SUFFIX}"

# @set CONFIG_VM_REGISTRY_DIR_PATH string Путь до директории реестра виртуальных машин
export CONFIG_VM_REGISTRY_DIR_PATH="${HOME_VPN_PROJECT_ROOT}/vm"

# @set CONFIG_NETWORK_INTERFACE_INTERNET string Имя сетевого интерфейса через который осуществляется выход в интернет. Если не задан, то будет определён автоматически
export CONFIG_NETWORK_INTERFACE_INTERNET=""

# @set CONFIG_NETWORK_INTERFACE_LOCAL string Имя сетевого интерфейса через который осуществляется выход в локальную сеть. Если не задан, то будет определён автоматически
export CONFIG_NETWORK_INTERFACE_LOCAL=""

# @set CONFIG_OVMF_VERSION string Версия EDK2/OVMF используемая для запуска виртуальной машины с UEFI. Git-тег из репозитория https://github.com/tianocore/edk2.git
export CONFIG_OVMF_VERSION="edk2-stable202508.01"
