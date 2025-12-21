#!/bin/bash

## @brief Функции работы с автозапуском (при старте ОС)


## @brief Установить cron
## details https://habr.com/ru/articles/933574/
##         https://man7.org/linux/man-pages/man1/crontab.1.html
##         https://man7.org/linux/man-pages/man5/crontab.5.html
## @retval 0 - успешно
function cron_setup() {
    if is_termux || is_msys; then
        return 0
    fi

    package_manager_install_packages "cron" || return $?
    return 0
}