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
3. пользователя "удерживающего" UDP порт открытым зовут watchdog (он автоматически создаётся при запуске скрипта
   setup-easy-rsa.sh)

fixme utopia расписать алгоритм + UML (mermaid)

## 2.1 Как понять что удастся обойти NAT

NAT удастся обойти если:

- NAT отсутствует
- NAT настроен в режиме **Full-cone**
- NAT настроен в режиме **Restricted cone**
- NAT настроен в режиме **Restricted port cone**

Проверить возможность обхода NAT можно при помощи скрипта main.py (команда check)

```bash

$ python3.8 main.py check
STUN server: stun.l.google.com:19302
NAT type: Full Cone
UDP hole punching: True
My external IP address and port: 78.106.192.197:63016

```

Если "UDP hole punching: True", то NAT удастся обойти.

## 2.2 Стороннее ПО для установки

Понять [какому пакету принадлежит данная команда](https://askubuntu.com/questions/13792/finding-out-what-package-a-command-came-from)
можно так (пример, для команды ip)

```bash

dpkg -S $(which ip)

```

### 2.2.1 Ubuntu 18.04 LTS (bionic)

```bash

sudo apt-get install python3.8 openvpn wget tar python3-venv python3-pip qemu xvnc4viewer procps iptables iproute2 dnsmasq-base procps

sudo python3.8 -m pip install pip --force-reinstall --ignore-installed

sudo pip3.8 install 'pystun3==1.0.0' --force-reinstall --ignore-installed

sudo pip3.8 install 'python-iptables==1.0.0' --force-reinstall --ignore-installed

sudo pip3.8 install 'psutil==5.9.1' --force-reinstall --ignore-installed

```

dnsmasq-base - dhcp сервер использумый для раздачи ip адресов внутри сетевого моста к которому привязаны виртуальные машины

xvnc4viewer ---> xtigervncviewer

fixme utopia Что нужно установить для KVM?
https://ubuntu.com/blog/kvm-hyphervisor

procps - для утилиты sysctl которая используется для записи параметров ядра

[Про установку pip для версии Python отличной от умолчательной](https://stackoverflow.com/a/63207387)

[STUN клиент для Python (pystun3)](https://pypi.org/project/pystun3/)

[iptables (linux firewall) обёртка для Python (python-iptables)](https://pypi.org/project/python-iptables/)

[Утилиты работы с процессами (psutil)](https://pypi.org/project/psutil/)

https://community.openvpn.net/openvpn/wiki/UnprivilegedUser#RunOpenVPNwithinunprivilegedpodmancontainer
https://openvpn.net/community-resources/reference-manual-for-openvpn-2-4/

https://stty.io/2019/05/13/qemu-vm-wireguard-vpn-tun-tap-networking/
https://www.linux.org.ru/forum/admin/5709331
https://askubuntu.com/questions/544065/routing-problem-openvpn-kvm
http://sassan.me.uk/blog/qemu-and-openvpn-secure-and-convenient-remote-access-to-virtual-servers/

https://openvpn.net/community-resources/ethernet-bridging/

Wireless bridge on KVM virtual machine

https://bbs.archlinux.org/viewtopic.php?id=207907

## 2.3 Настройка Telegram-бота

Используем Telegram-бота для отправки IP адреса/порта VPN сервера в специальную группу (OpenVpnChatBot)

[Настройка Telegram-бота](https://medium.com/javarevisited/sending-a-message-to-a-telegram-channel-the-easy-way-eb0a0b32968)
.

[Получить chat_id группы](https://perfluence.net/blog/article/kak-uznat-id-telegram).

Полученную конфигурацию записываем в [telegram-bot.config.json](telegram-bot.config.json).

## 2.4 Настройка OpenVpn сервера

## 2.5 Настройка OpenVpn клиента

OpenVpn клиент с [официального сайта](https://openvpn.net/vpn-client/)

### 2.5.1 Android клиент

OpenVpn клиент установить [отсюда](https://play.google.com/store/apps/details?id=net.openvpn.openvpn)

### 2.5.2 iOS клиент

### 2.5.3 Windows клиент

### 2.5.4 Linux клиент

### 2.5.5 MacOS клиент

## 2.6 Настройка виртуальных машин Qemu

```bash

sudo qemu-system-x86_64 -enable-kvm -m 4096 -cdrom ~/Загрузки/linuxmint-20.2-cinnamon-64bit.iso -vga std  -vnc 127.0.0.1:2 -cpu host -device virtio-net,netdev=vmnic -netdev tap,id=vmnic,ifname=vnet0,script=no,downscript=no

```

Подробно про параметры запуска виртуальной машины Qemu

- **-enable-kvm**
  Активировать KVM
- **-m 4096**
  Выделить гостевой ОС 4096 МБ оперативной памяти
- **-vga std**
  Использовать графический адаптер (VGA card) std, подробности
  см. [здесь](https://www.qemu.org/docs/master/system/invocation.html#hxtool-3)
- **-vnc 127.0.0.1:2**
  Активировать VNC сервер для доступа к гостевой ОС на localhost, порту 5902 (5900 + 2), подробности
  см. [здесь](https://www.qemu.org/docs/master/system/invocation.html#hxtool-3)
- **-cpu host**
  XXX

Подлючиться к VNC серверу гостевой ОС можно при помощи

```bash

vncviewer -4 127.0.0.1:2

```

### 2.6.1 Настройка сетевого адаптера виртальной машины

[Статья](http://sassan.me.uk/blog/qemu-and-openvpn-secure-and-convenient-remote-access-to-virtual-servers/) описывающая
подключение виртуальных машин Qemu к OpnVpn (Routing or Bridging?).

[Статья](https://superuser.com/a/1486963) описывающая настройку сетевого интерфейса виртуальной машины Qemu на работу
через WiFi хостовой ОС.

https://bbs.archlinux.org/viewtopic.php?id=207907

https://wiki.gentoo.org/wiki/QEMU/Bridge_with_Wifi_Routing

https://wiki.gentoo.org/wiki/QEMU/Options#Virtual_network_cable_.28TAP.29

### 2.6.2 Проброс хостовой видеокарты в гостевую ОС

Возможные варианты проброса видеокарты в гостевую ОС
описаны [здесь](https://wiki.archlinux.org/title/QEMU/Guest_graphics_acceleration).

fixme utopia Будем пробовать все подходы

### 2.6.3 Настройка VNC сервера гостевой ОС

Основополагающая [статья](https://habr.com/ru/company/ruvds/blog/510860/).

https://hackware.ru/?p=12588

https://losst.ru/ustanovka-vnc-server-v-ubuntu-18-04

### 2.6.4 Настройка RDP сервера гостевой ОС

Основополагающая [статья](https://habr.com/ru/company/ruvds/blog/512878/).

#### Windows Home

У "домашних" версий Windows необходимо активировать RDP сервер при
помощи [RDP Wrapper](https://github.com/stascorp/rdpwrap).

#### Ubuntu 20.04

https://setiwik.ru/kak-ustanovit-xrdp-na-ubuntu-20-04/

#### Linux Mint 20.2

https://www.avoiderrors.com/easily-remote-connect-to-linux-mint-20-2-from-any-os/

# 3 Инсталяция системы

1. сконфигурировать пути в open-vpn.config.json, **если необходимо**
2. сгенерирвоать сертификаты для OpenVpn сервера

```bash

sudo ./setup-easy-rsa.sh

```

3. создать сертификаты для нового пользователя

```bash

sudo ./build-client.sh имя_пользователя

```

4. запустить систему OpenVpn сервер

Права суперпользователя необходимы для запуска OpenVpn сервера.

```bash

sudo python3.8 main.py run

```

5. сгенерировать ovpn конфигурацию для пользователя, которому сгенерировали сертификаты на шаге (3)

```bash

python3.8 main.py user_ovpn имя_пользователя

```

6. запустить OpenVpn клиента с конфигурацией полученной на шаге (5)

```bash

openvpn --config client-имя_пользователя.ovpn

```

# 4 Возможные конфигурации клиентского оборудования

# 5 Хотелки

1. Следить за температорой видеокарты для виртуальной машины
2. Описать как запустить игры на виртуальной машине с проброшенной видеокартой (Windows)
