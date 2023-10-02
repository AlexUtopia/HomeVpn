# HomeVpn

# 1 Цели

1. Дать доступ к домашней сети и машинам внутри неё всем клиентам VPN сети
2. Дать доступ клиентам VPN к виртуальным машинам
3. Аккумулировать и распределить (внутрисетевые) вычислительные мощности VPN (CPU, RAM, HDD/SSD, GPU) всем клиентам
4. Снизить затраты на наличное оборудование (за счёт снижения требований к этому оборудованию) всех клиентов VPN
5. Снизить затраты на администрирвоание наличного парка оборудования
6. Поддерживаемые платформы
 - LinuxMint 19.3 / Ubuntu 18.04 / Debian ???
 - ArchLinux (проверить)
 - CentOs (проверить на рабочей тачке)
 - Fedora
 - Windows 7+
 - Android/termux
 - Windows/msys2
7. Версия python 3.8+

https://pkgs.org/

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

sudo apt-get install python${PYTHON_VERSION} openvpn wget tar python3-venv python3-pip qemu qemu-system tigervnc-viewer procps iptables iproute2 dnsmasq-base coreutils -y

sudo python${PYTHON_VERSION} -m pip install pip --force-reinstall --ignore-installed

sudo pip${PYTHON_VERSION} install 'pystun3==1.0.0' --force-reinstall --ignore-installed

sudo pip${PYTHON_VERSION} install 'python-iptables==1.0.0' --force-reinstall --ignore-installed

sudo pip${PYTHON_VERSION} install 'psutil==5.9.1' --force-reinstall --ignore-installed

sudo pip${PYTHON_VERSION} install 'netaddr==0.8.0' --force-reinstall --ignore-installed

sudo pip${PYTHON_VERSION} install 'randmac==0.1' --force-reinstall --ignore-installed

sudo pip${PYTHON_VERSION} install 'transmission-rpc==4.2.0' --force-reinstall --ignore-installed

sudo pip${PYTHON_VERSION} install 'semantic_version==2.10.0' --force-reinstall --ignore-installed

sudo pip${PYTHON_VERSION} install 'os-release==1.0.1' --force-reinstall --ignore-installed

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


#### 2.6.2.1 Paravirtualization при помощи virtio и Mesa3D/VirGL

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

Подробный обзор SR-IOV

https://projectacrn.github.io/latest/tutorials/sriov_virtualization.html


Настроить виртуальные SR-IOV устройства по инструкции

https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/7/html/virtualization_deployment_and_administration_guide/sect-pci_devices-pci_passthrough

```bash

cat /sys/class/graphics/fb0/device/sriov_totalvfs

```

Обзорная статья по linux sysfs

https://man7.org/linux/man-pages/man5/sysfs.5.html

Проверить работоспособность vfio

https://wiki.archlinux.org/title/PCI_passthrough_via_OVMF

Гайд по Single GPU Passthrough

https://www.youtube.com/watch?v=hQL5h5GteTY&feature=youtu.be

https://gitlab.com/risingprismtv/single-gpu-passthrough/-/wikis/home

Linux vfio

https://docs.kernel.org/driver-api/vfio.html

https://www.ibm.com/docs/en/linux-on-systems?topic=through-pci

https://www.reddit.com/r/VFIO/comments/nbdeov/when_to_use_vfiopcibind_vs_vfiopcinew_id/

https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-bus-pci

Проверка наличия builtin kernel module vfio

https://askubuntu.com/questions/1247058/how-do-i-confirm-that-vfio-is-working-in-20-04

https://superuser.com/questions/577307/how-to-get-a-list-of-active-drivers-that-are-statically-built-into-the-linux-ker

```bash

qemu-system-$(uname -m) -device vfio-pci,help

```

Не получается активировать SR-IOV

```bash

sudo echo 3 > /sys/class/graphics/fb0/device/sriov_numvfs

```

https://www.reddit.com/r/VFIO/comments/twx11c/another_thread_about_sriov_on_intel_iris_xe_gpu/

https://github.com/strongtz/i915-sriov-dkms

У моего ядра (драйвер GPU i915) нет поддержки SR-IOV - отсюда и не работает

https://github.com/intel/linux-intel-lts/tree/lts-v5.15.49-adl-linux-220826T092047Z

https://github.com/intel/linux-intel-lts/commit/daaac8806cd0e918ec4fe1883f4631ce9a9bc542

https://community.intel.com/t5/Graphics/SR-IOV-support-for-intel-Iris-Xe-Graphics-on-i7-1165G7/m-p/1294449/highlight/true#M98498

https://github.com/intel/linux-intel-lts/issues/33#issuecomment-1176996341

```bash

sudo apt-get install linux-source

```

#### 2.6.2.3 Virtual GPU при помощи GVT-g

Основополагающая [статья](https://wiki.archlinux.org/title/Intel_GVT-g).
Подробное руководство по настройке GVT-g с [хабра](https://habr.com/ru/post/437270/).
[Руководство с linux.org.ru](https://www.linux.org.ru/gallery/screenshots/16793722).
Поддерживаемые GVT-g [GPU](https://open-iov.org/index.php/GPU_Support).

GVT-g не поддерживается для Tiget Lake процессоров Intel

https://github.com/intel/gvt-linux/issues/174#issuecomment-1288728895

GVT-g попробовать на ноутбуке Галины (Intel N4120 (UHD Graphics 600))

https://www.youtube.com/watch?v=RbLN7kZiAQ0


#### 2.6.2.4 Virtual GPU при помощи GVT-d

https://projectacrn.github.io/latest/tutorials/gpu-passthru.html

https://www.ibm.com/docs/en/linux-on-systems?topic=through-pci

https://github.com/cy4n1c/single-intel-gpu-passthrough

Build-in kernel module нельзя загружать/выгружать, только конфигурировать через параметры загрузки ядра
(/etc/default/grub GRUB_CMDLINE_LINUX).
Команды modprobe, insmod, rmmod, modinfo, lsmod для таких модулей не работают.

https://www.xmodulo.com/find-information-builtin-kernel-modules-linux.html

Удалось добиться захвата gpu драйвером vfio-pci, осталось только пробросить gpu в виртуальную машину.
Попробовать проброс видео в BIOS и UEFI режиме.
После изменения конфига загрузки запустить

```bash

sudo update-grub

```

https://pve.proxmox.com/wiki/PCI_Passthrough

https://superuser.com/questions/1350451/isolate-single-device-into-separate-iommu-group-for-pci-passthrough


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


### 2.6.5 SSH

https://www.simplified.guide/ssh/x11-forwarding-as-root


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

1. Следить за температурой видеокарты для виртуальной машины
2. Описать как запустить игры на виртуальной машине с проброшенной видеокартой (Windows)


# 7 Установка операционных систем

## 7.1 Windows

https://wiki.archlinux.org/title/QEMU#Preparing_a_Windows_guest

https://devsday.ru/blog/details/10111
https://github.com/virtio-win/kvm-guest-drivers-windows/issues/785

### 7.1.1 Разрешить ICMP пакеты

https://www.howtogeek.com/howto/windows-vista/allow-pings-icmp-echo-request-through-your-windows-vista-firewall/


## 7.2 Linux (Ubuntu)

### 7.2.1 Установка новой версии ядра linux

Инструкцию см. [здесь](https://linuxhint.com/install-upgrade-latest-kernel-ubuntu-22-04/)


## 7.3 Android

### 7.3.1 BlissOS

Официальный [сайт](https://blissos.org/).
Скачать iso образы можно [здесь](https://blissos.org/index.html#download).

Плюсы
 - бесплатная свободно распространяемая версия Android для x86 платформы
 - доступен Android 11 и 12 (альфа)
 - актуальное ядро linux 5.4, возможно пробросить PCI устройство
 - доступна GMS сборка где присутствуют Google Play Services

Минусы
 - надо тестировать, пока не обнаружил

https://docs.blissos.org/install-bliss-os/install-in-a-virtual-machine/install-in-qemu


### 7.3.2 Android-x86

Официальный [сайт](https://www.android-x86.org/).
Скачать iso образы можно [здесь](https://sourceforge.net/projects/android-x86/files/).

Плюсы
 - бесплатная свободно распространяемая версия Android для x86 платформы
 - вроде как для Android-x86 9 [присутствуют Google Play Services](https://www.youtube.com/watch?v=uYVlVLC660M)

Минусы
 - проект плохо развивается, в актуальной разработке Android [8.1](https://www.android-x86.org/releases/releasenote-8-1-r6.html) и [9](https://www.android-x86.org/releases/releasenote-9-0-r2.html)
 - используется неактуальное ядро linux 4.19


### 7.3.3 LineageOS

[Вики](https://ru.wikipedia.org/wiki/LineageOS) про LineageOS.

Плюсы
 - бесплатная свободно распространяемая версия Android для большого круга платформ
 - доступен Android 11 и 12

Минусы
 - для emulator необходимо [собрать ОС](https://wiki.lineageos.org/emulator)
 - Google Play Services необходимо устанавливать вручную по [инструкции](https://wiki.lineageos.org/gapps)


### 7.3.4 Android Studio emulator

Скачать Android Studio и запустить актуальные версии Android в emulator (под капотом модифицированный qemu 2.12.0)

```bash

~/Android/Sdk/emulator/emulator -qemu -version

```

Запустить AVD через командную строку можно так

```bash

~/Android/Sdk/emulator/emulator -avd <название AVD>

```

Подробней про параметры командной строки эмулятора см. [здесь](https://developer.android.com/studio/run/emulator-commandline).

Плюсы
 - всегда актуальная и работоспособная версия Android от Google
 - большая вариативность версий и классов Android
 - наличие Google Play Services

Минусы
 - запускается только под emulator и никак больше
 - завязка на emulator который использует неактуальную версию qemu (2.12.0)
 - непонятна возможность настройки emulator под нужны проекта HomeVpn
 - непонятна возможность проброса PCI устройства (нас интересует GPU)


### 7.3.5 Android Studio AVD by actual qemu

Нахожусь в процессе изысканий, с первой попытки не заработало.
Пытаюсь запустить Android TV 12.

```bash

export AVD_DIR=~/Android/Sdk/system-images/android-31/android-tv/x86

sudo qemu-system-$(uname -m) -enable-kvm -m 1024 -kernel ${AVD_DIR}/kernel-ranchu-64 -initrd ${AVD_DIR}/ramdisk.img -append "console=ttyS0 panic=100 module_blacklist=cfg80211,btusb,btrtl,btintel,ac97_bus" -nographic -cpu host

```

При помощи опции ядра module_blacklist отключил все модули ядра что пытались загрузиться.

Падает процесс init. В интернете однозначного рецепта что делать нет.

```
[    0.666946] Run /init as init process
[    0.669645] init: init first stage started!
[    0.672207] init: Loading module /lib/modules/ac97_bus.ko with args ''
[    0.674006] Module ac97_bus is blacklisted
[    0.675100] init: Failed to insmod '/lib/modules/ac97_bus.ko' with args '': Operation not permitted
[    0.677603] init: LoadWithAliases was unable to load ac97_bus
[    0.679455] init: Copied ramdisk prop to /second_stage_resources/system/etc/ramdisk/build.prop
[    0.681917] init: [libfs_mgr]ReadFstabFromDt(): failed to read fstab from dt
[    0.683885] init: [libfs_mgr]ReadDefaultFstab(): failed to find device default fstab
[    0.685984] init: Failed to create FirstStageMount failed to read default fstab for first stage mount
[    0.688377] init: Failed to mount required partitions early ...
[    0.689874] Kernel panic - not syncing: Attempted to kill init! exitcode=0x00007f00
[    0.691629] CPU: 0 PID: 1 Comm: init Not tainted 5.10.66-android12-9-00022-g2d6a43c0364d-ab7992900 #1
[    0.693765] Hardware name: QEMU Standard PC (i440FX + PIIX, 1996), BIOS 1.10.2-1ubuntu1 04/01/2014
[    0.695783] Call Trace:
[    0.696371]  panic+0x125/0x40b
[    0.697043]  do_exit+0xb9c/0xc20
[    0.697694]  ? __ia32_sys_wait4.cfi_jt+0x8/0x8
[    0.698603]  do_group_exit+0xd0/0xe0
[    0.699304]  ? __ia32_sys_wait4.cfi_jt+0x8/0x8
[    0.699918]  __do_sys_exit_group+0xf/0x10
[    0.700535]  __se_sys_exit_group+0x9/0x10
[    0.701628]  __ia32_sys_exit_group+0xc/0x10
[    0.702662]  __do_fast_syscall_32+0xab/0xe0
[    0.703590]  do_fast_syscall_32+0x32/0x70
[    0.704627]  do_SYSENTER_32+0x1b/0x20
[    0.705600]  entry_SYSENTER_compat_after_hwframe+0x4d/0x5f
[    0.707074] RIP: 0023:0xf7f23509
[    0.707933] Code: b8 01 10 06 03 74 b4 01 10 07 03 74 b0 01 10 08 03 74 d8 01 00 00 00 00 00 00 00 00 00 00 00 00 00 51 52 55 89 e5 0f 34 cd 80 <5d> 5a 59 c3 90 90 90 90 66 2e 0f 1f 84 00 00 00 00 00 0f 1f 44 00
[    0.712929] RSP: 002b:00000000ffbbb7a4 EFLAGS: 00000282 ORIG_RAX: 00000000000000fc
[    0.714930] RAX: ffffffffffffffda RBX: 000000000000007f RCX: 0000000000000001
[    0.716819] RDX: 0000000000000006 RSI: 0000000000000001 RDI: 0000000000000001
[    0.718621] RBP: 00000000ffbbb898 R08: 0000000000000000 R09: 0000000000000000
[    0.720326] R10: 0000000000000000 R11: 0000000000000000 R12: 0000000000000000
[    0.721960] R13: 0000000000000000 R14: 0000000000000000 R15: 0000000000000000
[    0.723610] Kernel Offset: 0x18a00000 from 0xffffffff81000000 (relocation range: 0xffffffff80000000-0xffffffffbfffffff)
[    0.726070] Rebooting in 100 seconds..
```

Нужно попробовать получить root для AVD и посмотреть как выглядит загрузка linux на emulator (dmesg).
Мне не нравится содержимое ramdisk.img - там пустые папки.  

```bash

export ANDROID_SDK=~/Android/Sdk
${ANDROID_SDK}/platform-tools/adb shell
generic_x86:/ $ dmesg

```

Получить root для AVD можно [так](https://github.com/newbit1/rootAVD).

Прочие полезные статьи по ручной загрузке linux для qemu

http://nickdesaulniers.github.io/blog/2018/10/24/booting-a-custom-linux-kernel-in-qemu-and-debugging-it-with-gdb/

https://fadeevab.com/how-to-setup-qemu-output-to-console-and-automate-using-shell-script/

https://qemu.readthedocs.io/en/latest/about/removed-features.html

https://source.android.com/docs/core/architecture/kernel/mounting-partitions-early

https://source.android.com/docs/core/architecture/kernel/generic-kernel-image

https://developer.android.com/studio/run/emulator-acceleration

https://elixir.bootlin.com/linux/v5.10.66/source

https://stackoverflow.com/questions/65415511/android-kernel-build-flow-with-gki-introduced-from-android-11

https://www.kernel.org/doc/html/v5.10/admin-guide/kernel-parameters.html

Плюсы
 - все те же самые плюсы, что и у метода 7.3.4
 - независимость от emulator
 - для поддержки необходимого спектра реальных устройств нужно [пересобрать](https://source.android.com/docs/setup/build/building-kernels) целевое ядро linux (добавить intel GPU driver i915)

Минусы
 - очень сложно разобраться что к чему даже при наличии опыта
 - работает только через qemu (для проекта HomeVpn минусом не является)
