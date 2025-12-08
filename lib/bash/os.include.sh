#!/bin/bash

## @brief Базовые функции получения информации о текущей ОС


## @brief Проверить можно ли выполнить команду от имени администратора
## @details Работает для Linux, Android/termux
## @details su   : termux-tools / util-linux
##          sudo : tsu / sudo
## https://github.com/termux/termux-tools/blob/master/scripts/su.in
## @retval 0 - можно выполнить команду от имени администратора, 1 - нет
function is_admin_rights_available() {
    su --version &> "/dev/null" || return $?
    return 0
}

## @brief Получить название текущей ОС
## @details Результат - строка в нижнем регистре
## @return Название текущей ОС
## @retval 0 - успешно
function get_os_name() {
    local RESULT=""
    RESULT=$(uname -o) || return $?
    echo "${RESULT,,}"
    return 0
}

## @brief Закэшированное имя текущей ОС
OS_NAME=$(get_os_name)

## @brief Получить название архитектуры ОС
## @details Результат - строка в нижнем регистре
## @return Название архитектуры ОС
## @retval 0 - успешно
function get_machine_name() {
    local RESULT=""
    RESULT=$(uname -m) || return $?
    echo "${RESULT,,}"
    return 0
}

## @brief Закэшированная архитектура текущей ОС
OS_MACHINE_NAME=$(get_machine_name)

## @brief Проверить является ли текущая ОС Linux
## @retval 0 - текущая ОС Linux, 1 - нет
function is_linux() {
   if [[ "${OS_NAME}" == *"linux"* ]]; then
       return 0
   fi
   return 1
}

## @brief Проверить является ли текущая ОС Android/termux
## @retval 0 - текущая ОС Android/termux, 1 - нет
function is_termux() {
   if [[ "${OS_NAME}" == *"android"* ]]; then
       return 0
   fi
   return 1
}

## @brief Проверить является ли текущая ОС Windows/MSYS2
## @retval 0 - текущая ОС Windows/MSYS2, 1 - нет
function is_msys() {
   if [[ "${OS_NAME}" == *"msys"* ]]; then
       return 0
   fi
   return 1
}

## @brief Проверить является ли текущая ОС Windows/Cygwin
## @retval 0 - текущая ОС Windows/Cygwin, 1 - нет
function is_cygwin() {
   if [[ "${OS_NAME}" == *"cygwin"* ]]; then
       return 0
   fi
   return 1
}

## @brief Получить название дистрибутива Linux
## @details Работает для Linux
## @details https://www.freedesktop.org/software/systemd/man/latest/os-release.html
## @details Результат - строка в нижнем регистре
## @return Название дистрибутива Linux
## @retval 0 - успешно
function get_linux_distro_name() {
   source "/etc/os-release" || return $?

   if [[ -n "${UBUNTU_CODENAME}" ]]; then
       # Для Ubuntu-based дистрибутивов linux (типа Linix Mint) всегда используются ubuntu PPA
       echo "ubuntu"
   else
       echo "${ID,,}"
   fi
   return 0
}

## @brief Получить название версии дистрибутива Linux
## @details Работает для Linux
## @details https://www.freedesktop.org/software/systemd/man/latest/os-release.html
## @details Результат - строка в нижнем регистре
## @return Название версии дистрибутива Linux
## @retval 0 - успешно
function get_linux_distro_codename_or_version() {
   source "/etc/os-release" || return $?

   if [[ -n "${UBUNTU_CODENAME}" ]]; then
       echo "${UBUNTU_CODENAME,,}"
   elif [[ -n "${VERSION_CODENAME}" ]]; then
       echo "${VERSION_CODENAME,,}"
   else
       echo "${VERSION_ID,,}"
   fi
   return 0
}
