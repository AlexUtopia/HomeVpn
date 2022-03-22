# HomeVpn

# 1 Цели

1. Дать доступ к домашней сети и машинам внутри неё всем клиентам VPN сети
2. Дать доступ клиентам VPN к виртуальным машинам
3. Аккумулировать и распределить (внутрисетевые) вычислительные мощности VPN (CPU, RAM, HDD/SSD, GPU) всем клиентам
4. Снизить затраты на наличное оборудование (за счёт снижения требований к этому оборудованию) всех клиентов VPN
5. Снизить затраты на администрирвоание наличного парка оборудования


# 2 Реализация

[Основополагающая статья](https://habr.com/ru/post/482888/).

Относительно оригинала здесь:
1. python3.8 заместо bash
2. отправка IP адреса/порта VPN сервера не на email, а в Telegram группу
3. пользователя "удерживающего" UDP порт открытым зовут watchdog (он автоматически создаётся при запуске скрипта setup-easy-rsa.sh)

fixme utopia расписать алгоритм + UML (mermaid)

## 2.1 Как понять что удастся обойти NAT



## 2.2 Стороннее ПО для установки

### 2.2.1 Ubuntu 18.04 LTS (bionic)

```sh

sudo apt-get install python3.8 openvpn wget tar python3-venv python3-pip

sudo python3.8 -m pip install pip --force-reinstall

sudo pip3.8 install 'pystun3==1.0.0' --force-reinstall

```

[Про установку pip для версии Python отличной от умолчательной](https://stackoverflow.com/a/63207387)
[STUN клиент для Python (pystun3)](https://pypi.org/project/pystun3/)

https://community.openvpn.net/openvpn/wiki/UnprivilegedUser#RunOpenVPNwithinunprivilegedpodmancontainer
https://openvpn.net/community-resources/reference-manual-for-openvpn-2-4/

https://stty.io/2019/05/13/qemu-vm-wireguard-vpn-tun-tap-networking/
https://www.linux.org.ru/forum/admin/5709331
https://askubuntu.com/questions/544065/routing-problem-openvpn-kvm
http://sassan.me.uk/blog/qemu-and-openvpn-secure-and-convenient-remote-access-to-virtual-servers/

https://openvpn.net/community-resources/ethernet-bridging/


Wireless bridge on KVM virtual machine
https://bbs.archlinux.org/viewtopic.php?id=207907
https://superuser.com/questions/694929/wireless-bridge-on-kvm-virtual-machine

## 2.3 Настройка Telegram-бота

Используем Telegram-бота для отправки IP адреса/порта VPN сервера в специальную группу (OpenVpnChatBot)

[Настройка Telegram-бота](https://medium.com/javarevisited/sending-a-message-to-a-telegram-channel-the-easy-way-eb0a0b32968).

[Получить chat_id группы](https://perfluence.net/blog/article/kak-uznat-id-telegram).

Полученную конфигурацию записываем в [telegram-bot.config.json](telegram-bot.config.json).


## 2.4 Настройка OpenVpn сервера


## 2.5 Настройка OpenVpn клиента


### 2.5.1 Android клиент


### 2.5.2 iOS клиент


### 2.5.3 Windows клиент


## 2.6 Настройка виртуальных машин Qemu


### 2.6.1 Настройка сетевого адаптера виртальной машины


### 2.6.2 Проброс видеокарты в виртуальную машину


# 3 Инсталяция системы


# 4 Возможные конфигурации клиентского оборудования


# 5 Хотелки

1. Следить за температорой видеокарты для виртуальной машины
2. Описать как запустить игры на виртуальной машине с проброшенной видеокартой (Windows)
