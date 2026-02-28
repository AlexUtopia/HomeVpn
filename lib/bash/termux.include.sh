#!/bin/bash

## @brief Функции работы с Android/termux
## https://github.com/termux/termux-app
## https://f-droid.org/ru/packages/com.termux/
## https://wiki.termux.dev/wiki/Main_Page


## @brief Установить репозитории пакетов
##        x11  : https://github.com/termux/termux-packages/tree/master/x11-packages
##               https://packages.termux.dev/apt/termux-x11/
##        root : https://github.com/termux/termux-packages/tree/master/root-packages
##               https://packages.termux.dev/apt/termux-root/
## @retval 0 - успешно
function termux_apt_repo_packages_setup() {
    package_manager_install_packages "x11-repo root-repo" || return $?
    apt update || return $?
    return 0
}

## @brief Установить пакеты работы с пользователями
## @retval 0 - успешно
function termux_user_packages_setup() {
    package_manager_install_packages "termux-auth" || return $?
    return 0
}

## @brief Установить пакеты работы со службами
## @retval 0 - успешно
function termux_service_packages_setup() {
    package_manager_install_packages "termux-services" || return $?
    return 0
}

## @brief Установить Android/termux специфичные пакеты
## @retval 0 - успешно
function termux_specific_packages_setup() {
    package_manager_install_packages "termux-tools termux-api proot" || return $?
    return 0
}

## @brief Установить графическое окружение для Android/termux
## @details https://wiki.termux.com/wiki/Graphical_Environment
## @retval 0 - успешно
function termux_gui_packages_setup() {
    package_manager_install_packages "xfce4 xfce4-terminal" || return $?
    return 0
}

## @brief Получить домашнюю директорию пользователя
## @details В Android/termux возможен только один пользователь, поэтому имя пользователя игнорируется
##          https://wiki.termux.com/wiki/Differences_from_Linux
## @retval 0 - успешно
function termux_user_get_home_dir_path() {
    echo ~
    return 0
}

## @brief Проверить задан ли пароль у пользователя
## @details В Android/termux возможен только один пользователь, поэтому имя пользователя игнорируется
##          https://wiki.termux.com/wiki/Differences_from_Linux
## @retval 0 - пароль задан; 1 - нет
function termux_user_is_exists_password() {
    local USER_HOME_DIR_PATH=""
    USER_HOME_DIR_PATH=$(termux_user_get_home_dir_path 2> "/dev/null") || return $?
    # https://github.com/termux/termux-auth/blob/master/termux-auth.h#L13C30-L13C41
    local USER_PASSWORD_FILE_PATH="${USER_HOME_DIR_PATH}/.termux_authinfo"
    if [[ -f "$USER_PASSWORD_FILE_PATH" ]]; then
        return 0
    fi
    return 1
}

## @brief Задать автозапуск служб по загрузке Android
## @details https://wiki.termux.com/wiki/Termux-services
## @details https://wiki.termux.com/wiki/Termux:Boot
## @retval 0 - успешно
function termux_autorun_serves_at_boot() {
    local AUTORUN_SERVICES_DIR_PATH="$(termux_user_get_home_dir_path)/.termux/boot"
    local AUTORUN_SERVICES_SCRIPT="autorun_services_at_boot.sh"

    local AUTORUN_SERVICES_SCRIPT_PATH="${AUTORUN_SERVICES_DIR_PATH}/${AUTORUN_SERVICES_SCRIPT}"

    fs_create_file "#!${SHELL}
termux-wake-lock
. \"${GLOBAL_CONFIG_ETC_PREFIX}/profile\"" "${AUTORUN_SERVICES_SCRIPT_PATH}" "" "rewrite_if_exist" || return $?
    fs_set_file_as_executable "${AUTORUN_SERVICES_SCRIPT_PATH}" || return $?
    return 0
}

## @brief Создать символические ссылки на внутренний и внешний накопитель Android
## @details https://wiki.termux.com/wiki/Internal_and_external_storage
## @details https://stackoverflow.com/questions/29789204/bash-how-to-get-real-path-of-a-symlink
## @details Внутренний накопитель               "${TARGET_DIR_PATH}/android-internal-storage"
##          Внешний накопитель (если доступен)  "${TARGET_DIR_PATH}/android-external-storage"
## @param [in] Путь до директории где создавать символические ссылки, необязательный аргумент (если не задано, = текущая директория)
## @retval 0 - успешно
function termux_set_symlinks_to_storage() {
    local TARGET_DIR_PATH="${1}"
    if [[ -z "${TARGET_DIR_PATH}" ]]; then
        TARGET_DIR_PATH="."
    fi

    # Вылезет запрос доступа к накопителю (Android).
    # Как только будет получено разрешение, в домашней директории появится директория storage
    termux-setup-storage || return $?
    local TERMUX_STORAGE_SYMLINKS_DIR_PATH="$(termux_user_get_home_dir_path)/storage"
    fs_wait_for_dir_creation "${TERMUX_STORAGE_SYMLINKS_DIR_PATH}" || return $?

    local ANDROID_INTERNAL_STORAGE_DIR_PATH="${TERMUX_STORAGE_SYMLINKS_DIR_PATH}/shared"
    if fs_wait_for_dir_creation "${ANDROID_INTERNAL_STORAGE_DIR_PATH}"; then
        ANDROID_INTERNAL_STORAGE_DIR_PATH=$(realpath "${ANDROID_INTERNAL_STORAGE_DIR_PATH}") || return $?
        if [[ -d "${ANDROID_INTERNAL_STORAGE_DIR_PATH}" ]]; then
            fs_create_symlink "${ANDROID_INTERNAL_STORAGE_DIR_PATH}" "${TARGET_DIR_PATH}/android-internal-storage" || return $?
        fi
    fi

    # external-1 -> /storage/9C33-6BBD/Android/data/com.termux/files
    # В итоге хотим получить /storage/9C33-6BBD
    sleep 1
    local ANDROID_EXTERNAL_STORAGE_DIR_PATH="${TERMUX_STORAGE_SYMLINKS_DIR_PATH}/external-1"
    if [[ -d "${ANDROID_EXTERNAL_STORAGE_DIR_PATH}" ]]; then
        ANDROID_EXTERNAL_STORAGE_DIR_PATH=$(realpath "${ANDROID_EXTERNAL_STORAGE_DIR_PATH}") || return $?
        ANDROID_EXTERNAL_STORAGE_DIR_PATH=$(realpath "${ANDROID_EXTERNAL_STORAGE_DIR_PATH}/../../../../") || return $?
        if [[ -d "${ANDROID_EXTERNAL_STORAGE_DIR_PATH}" ]]; then
            fs_create_symlink "${ANDROID_EXTERNAL_STORAGE_DIR_PATH}" "${TARGET_DIR_PATH}/android-external-storage" || return $?
        fi
    fi

    return 0
}

## @brief Название пакета termux для Android
TERMUX_PACKAGE_NAME="com.termux"

## @brief Скачиваемый apk termux
TERMUX_APK_FILE_NAME="${TERMUX_PACKAGE_NAME}_1022.apk"

## @brief Получить путь до apk termux
## @return путь до apk termux
## @retval 0 - успешно
function termux_get_apk_path() {
    echo "${GLOBAL_CONFIG_OPT_DIR_PATH}/termux/${TERMUX_APK_FILE_NAME}"
    return 0
}

## @brief Скачать apk termux
## @param [in] Путь для скачивания apk termux, необязательный аргумент (если не задано, = termux_get_apk_path())
## @retval 0 - успешно
function termux_download_apk() {
    local INSTALL_PATH="${1}"
    if [[ -z "${INSTALL_PATH}" ]]; then
        INSTALL_PATH=$(termux_get_apk_path) || return $?
    fi

    local DOWNLOAD_URL="https://f-droid.org/repo/${TERMUX_APK_FILE_NAME}"
    download_file "${DOWNLOAD_URL}" "${INSTALL_PATH}" "download_if_not_exist" || return $?
    return 0
}
