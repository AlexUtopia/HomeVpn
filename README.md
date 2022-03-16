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

```sh

sudo apt-get install python3.8 stun-client openvpn wget tar

```

https://community.openvpn.net/openvpn/wiki/UnprivilegedUser#RunOpenVPNwithinunprivilegedpodmancontainer
https://openvpn.net/community-resources/reference-manual-for-openvpn-2-4/

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
