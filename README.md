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

export PYTHON_VERSION=3.10

sudo apt-get install python${PYTHON_VERSION} openvpn wget tar python3-venv python3-pip qemu qemu-system tigervnc-viewer procps iptables iproute2 dnsmasq-base coreutils

sudo python${PYTHON_VERSION} -m pip install pip --force-reinstall --ignore-installed

sudo pip${PYTHON_VERSION} install 'pystun3==1.0.0' --force-reinstall --ignore-installed

sudo pip${PYTHON_VERSION} install 'python-iptables==1.0.0' --force-reinstall --ignore-installed

sudo pip${PYTHON_VERSION} install 'psutil==5.9.1' --force-reinstall --ignore-installed

sudo pip${PYTHON_VERSION} install 'netaddr==0.8.0' --force-reinstall --ignore-installed

sudo pip${PYTHON_VERSION} install 'randmac==0.1' --force-reinstall --ignore-installed

```

dnsmasq-base - dns/dhcp сервер использумый для раздачи ip адресов внутри сетевого моста к которому привязаны виртуальные машины

xvnc4viewer ---> xtigervncviewer

fixme utopia Что нужно установить для KVM?
https://ubuntu.com/blog/kvm-hyphervisor

procps - для утилиты sysctl которая используется для записи параметров ядра

coreutils - содержит утилиту uname

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

xtigervncviewer 127.0.0.1:2

```

Посмотреть список доступных устройств можно так (см. описание опции [-device](https://www.qemu.org/docs/master/system/invocation.html#hxtool-0))

```bash

qemu-system-$(uname -m) -device help

```

### 2.6.1 Настройка сетевого адаптера виртуальной машины

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


#### 2.6.2.1 Paravirtualization при помощи virtio и Mesa3G/VirGL

Настройка параметров qemu описана [здесь](https://wiki.archlinux.org/title/QEMU#virtio).

Технологии VirGL описана в [официальной доке](https://docs.mesa3d.org/drivers/virgl.html) на Mesa3D.

Проверка возможности аппаратного кодирования/декодирования видео описана [здесь](https://wiki.archlinux.org/title/Hardware_video_acceleration_(%D0%A0%D1%83%D1%81%D1%81%D0%BA%D0%B8%D0%B9)).

Отмечу что тут речь идёт только лишь о возможности аппаратного ускорения OpenGL,
при этом аппаратно ускорять кодирование/декодирование видео пока нельзя.
На самом деле это полуправда, т.к. в [релиз 0.10.0](https://gitlab.freedesktop.org/virgl/virglrenderer/-/releases/virglrenderer-0.10.0)
была добавлена эта возможность, но пакет [libvirglrenderer1](https://packages.ubuntu.com/search?searchon=sourcenames&keywords=virglrenderer)
для Ubuntu ещё не обновился на минимально требуемую версию.
Отсутствие аппаратного ускорения кодирования/декодирования видео может ухудшить возможности
виртуальной машины стать полноценным мультимедийным сервером, к примеру, для использования
в качестве Android TV приставки.
Ручную сборку актуального пакета virglrenderer я пока не рассматриваю.


Доступные опции для виртуальной видеокарты (vga) можно посмотреть так

```bash

qemu-system-$(uname -m) -device virtio-vga-gl,help

```

Доступные опции для виртуального дисплея sdl описаны [здесь](https://www.qemu.org/docs/master/system/invocation.html#hxtool-3).


#### 2.6.2.2 Virtual GPU при помощи LibVF.IO 

fixme utopia Попробовать

https://arccompute.com/blog/libvfio-commodity-gpu-multiplexing/

https://github.com/Arc-Compute/LibVF.IO/

https://www.youtube.com/watch?v=wqUjukaTqEg

https://www.youtube.com/watch?v=xbVKMQ1Rz2Y


### 2.6.3 Настройка VNC сервера гостевой ОС

Основополагающая [статья](https://habr.com/ru/company/ruvds/blog/510860/).

https://hackware.ru/?p=12588

https://losst.ru/ustanovka-vnc-server-v-ubuntu-18-04

https://losst.ru/avtozagruzka-linux

#### 2.6.3.1 VNC клиент Linux (гостевая ОС Linux)

#### 2.6.3.2 VNC клиент Linux (гостевая ОС Windows)

#### 2.6.3.3 VNC клиент Windows (гостевая ОС Linux)

#### 2.6.3.4 VNC клиент Windows (гостевая ОС Windows)

### 2.6.4 Настройка RDP сервера гостевой ОС

Основополагающая [статья](https://habr.com/ru/company/ruvds/blog/512878/).

#### Windows Home

У "домашних" версий Windows необходимо активировать RDP сервер при
помощи [RDP Wrapper](https://github.com/stascorp/rdpwrap).

#### Ubuntu 20.04

https://setiwik.ru/kak-ustanovit-xrdp-na-ubuntu-20-04/

#### Linux Mint 20.2

https://www.avoiderrors.com/easily-remote-connect-to-linux-mint-20-2-from-any-os/

### 2.6.4 Аппаратное ускорение OpenGL по SSH и VNC для гостевых ОС Linux

https://virtualgl.org/

https://www.turbovnc.org/

https://wiki.archlinux.org/title/VirtualGL

https://askubuntu.com/questions/1319317/run-all-applications-with-virtualgl-on-turbovnc


# 3 Инсталяция системы

1. настроить домашний роутер fixme utopia
2. сконфигурировать пути в open-vpn.config.json, **если необходимо**
3. сгенерировать сертификаты для OpenVpn сервера

```bash

sudo ./setup-easy-rsa.sh

```

4. создать сертификаты для нового пользователя

```bash

sudo ./build-client.sh имя_пользователя

```

5. запустить OpenVpn сервер

Права суперпользователя необходимы для запуска OpenVpn сервера.

```bash

sudo python3.8 main.py run

```

6. сгенерировать ovpn конфигурацию для пользователя, которому сгенерировали сертификаты на шаге (3)

```bash

python3.8 main.py user_ovpn имя_пользователя

```

7. запустить OpenVpn клиента на удалённом ПК с конфигурацией полученной на шаге (5)

```bash

openvpn --config client-имя_пользователя.ovpn

```

8. запустить виртуальную машину fixme utopia расписать работу с реестром виртуалок

9. подлючиться к виртуальной машине fixme utopia

 - пример ssh (расписать настройку на гостевой машине)
 - пример rdp (расписать настройку на гостевой машине)
 - пример vnc (расписать настройку на гостевой машине)

10. Проброс виртуальной машины в локальную сеть

http://rhd.ru/docs/manuals/enterprise/RHEL-4-Manual/security-guide/s1-firewall-ipt-fwd.html

## 3.1 Преднастроенные виртуальные машины

fixme utopia Выложить на google диск преднастроенные виртуальные машины (просто болванки)


# 4 Конфигурация

## 4.1 Конфигурация проекта

fixme utopia Описать содержимое open-vpn.config.json

## 4.2 Список используемых STUN серверов


## 4.3 Конфигурация OpenVpn сервера


## 4.4 Конфигурация OpenVpn клиента


# 5 Возможные конфигурации клиентского оборудования


# 6 Хотелки

1. Следить за температорой видеокарты для виртуальной машины
2. Описать как запустить игры на виртуальной машине с проброшенной видеокартой (Windows)
