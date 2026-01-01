#!/bin/bash

## @brief Настройки экземпляра проекта
## @details python скрипт получит конфигурацию из переменных окружения.
##
##          Путь до скрипта с настройками текущего экземпляра проекта:
##              os.environ['CONFIG_PROJECT_INSTANCE_FILE_PATH']
##
##          Настройки текущего экземпляра проекта (примеры):
##              os.environ['CONFIG_OPENVPN_SERVER_PORT'] # Порт openvpn сервера
##              os.environ['CONFIG_DNS_MY_HOST']         # Доменное имя хоста виртуальной машины


## @brief Имя экземпляра проекта
CONFIG_PROJECT_INSTANCE="HomeVpn"

## @brief Порт openvpn сервера (в рамках экземпляра проекта)
CONFIG_OPENVPN_SERVER_PORT=35000

## @brief Путь до директории данных экземпляра проекта
CONFIG_OPENVPN_DATA_DIR_PATH="${GLOBAL_CONFIG_OPT_DIR_PATH}/${CONFIG_PROJECT_INSTANCE}"

## @brief Путь до директории данных openvpn сервера (в рамках экземпляра проекта)
CONFIG_OPENVPN_SERVER_DATA_DIR_PATH="${CONFIG_OPENVPN_DATA_DIR_PATH}/server"

## @brief Путь до директории с логами openvpn сервера (в рамках экземпляра проекта)
CONFIG_OPENVPN_SERVER_LOG_DIR_PATH="${CONFIG_OPENVPN_SERVER_DATA_DIR_PATH}/logs"

## @brief Путь до файла конфигурации (.ovpn) openvpn сервера (в рамках экземпляра проекта)
CONFIG_OPENVPN_SERVER_CONFIG_FILE_PATH="${CONFIG_OPENVPN_SERVER_DATA_DIR_PATH}/server.ovpn"

## @brief Путь до директории с сертификатами (EasyRSA) openvpn сервера/клиента (в рамках экземпляра проекта)
CONFIG_EASYRSA_PKI_DIR_PATH="${CONFIG_OPENVPN_SERVER_DATA_DIR_PATH}/pki"

## @brief Шаблон пути до директории данных openvpn клиента (в рамках экземпляра проекта)
## @details %s заменяется на имя клиента
CONFIG_OPENVPN_CLIENT_DATA_DIR_PATH_TEMPLATE="${CONFIG_OPENVPN_DATA_DIR_PATH}/client/%s"

## @brief Шаблон пути до директории с логами openvpn клиента (в рамках экземпляра проекта)
## @details %s заменяется на имя клиента
CONFIG_OPENVPN_CLIENT_LOG_DIR_PATH_TEMPLATE="${CONFIG_OPENVPN_CLIENT_DATA_DIR_PATH_TEMPLATE}/logs"

## @brief Шаблон пути до файла конфигурации (.ovpn) openvpn клиента (в рамках экземпляра проекта)
## @details %s заменяется на имя клиента
CONFIG_OPENVPN_CLIENT_CONFIG_FILE_PATH_TEMPLATE="${CONFIG_OPENVPN_CLIENT_DATA_DIR_PATH_TEMPLATE}/client.ovpn"

## @brief Путь до файла куда записываются текущий публичный адрес и порт (в рамках экземпляра проекта)
CONFIG_MY_CURRENT_IP_ADDRESS_AND_PORT_FILE_PATH="${CONFIG_OPENVPN_SERVER_DATA_DIR_PATH}/my_current_ip_address_and_port.txt"

## @brief IP адрес и маска сетевого моста (в рамках экземпляра проекта)
CONFIG_NETWORK_BRIDGE_IP_ADDRESS_AND_MASK="172.20.0.5/16"

## @brief Путь до директории данных сетевого моста (в рамках экземпляра проекта)
CONFIG_NETWORK_BRIDGE_DATA_DIR_PATH="${CONFIG_OPENVPN_SERVER_DATA_DIR_PATH}/network_bridge"

## @brief Путь до директории данных DNS/DHCP сервера (в рамках экземпляра проекта)
CONFIG_DNS_DHCP_DATA_DIR_PATH="${CONFIG_NETWORK_BRIDGE_DATA_DIR_PATH}/dns_dhcp"

## @brief DNS суффикс для виртуальных машин (в рамках экземпляра проекта)
CONFIG_DNS_SUFFIX="${CONFIG_PROJECT_INSTANCE,,}.org"

## @brief Доменное имя хоста виртуальной машины (в рамках экземпляра проекта)
## @details Из виртуальной машины можно обратиться к её хосту по этому имени, а не по IP адресу
CONFIG_DNS_MY_HOST="myhost.${CONFIG_DNS_SUFFIX}"

## @brief Путь до директории реестра виртуальных машин
CONFIG_VM_REGISTRY_DIR_PATH="${HOME_VPN_PROJECT_ROOT}/vm"

## @brief URL на скачивание virtio драйверов для Windows
CONFIG_VIRTIO_WIN_DRIVERS_URL="https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso"

## @brief Имя сетевого интерфейса через который осуществляется выход в интернет
## @details Если не задан, то будет определён автоматически
CONFIG_NETWORK_INTERFACE_INTERNET=""

## @brief Имя сетевого интерфейса через который осуществляется выход в локальную сеть
## @details Если не задан, то будет определён автоматически
CONFIG_NETWORK_INTERFACE_LOCAL=""