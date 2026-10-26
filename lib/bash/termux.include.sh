#!/bin/bash

# @file termux.include.sh
# @brief Функции работы с Android/termux
# @description
# https://github.com/termux/termux-app
# https://f-droid.org/ru/packages/com.termux/
# https://wiki.termux.dev/wiki/Main_Page


# @description Установить репозитории пакетов
#        x11  : https://github.com/termux/termux-packages/tree/master/x11-packages
#               https://packages.termux.dev/apt/termux-x11/
#        root : https://github.com/termux/termux-packages/tree/master/root-packages
#               https://packages.termux.dev/apt/termux-root/
# @exitcode 0 успешно
function termux_apt_repo_packages_setup() {
    package_manager_install_packages "x11-repo root-repo" || return $?
    apt update || return $?
    return 0
}

# @description Установить пакеты работы с пользователями
# @exitcode 0 успешно
function termux_user_packages_setup() {
    package_manager_install_packages "termux-auth" || return $?
    return 0
}

# @description Установить пакеты работы со службами
# @exitcode 0 успешно
function termux_service_packages_setup() {
    package_manager_install_packages "termux-services" || return $?
    return 0
}

# @description Установить Android/termux специфичные пакеты
# @exitcode 0 успешно
function termux_specific_packages_setup() {
    package_manager_install_packages "termux-tools termux-api proot" || return $?
    return 0
}

# @description Установить графическое окружение для Android/termux
# https://wiki.termux.com/wiki/Graphical_Environment
# @exitcode 0 успешно
function termux_gui_packages_setup() {
    package_manager_install_packages "xfce4 xfce4-terminal" || return $?
    return 0
}

# @description Получить домашнюю директорию пользователя
# В Android/termux возможен только один пользователь, поэтому имя пользователя игнорируется
#         https://wiki.termux.com/wiki/Differences_from_Linux
# @exitcode 0 успешно
function termux_user_get_home_dir_path() {
    echo ~
    return 0
}

# @description Проверить задан ли пароль у пользователя
# В Android/termux возможен только один пользователь, поэтому имя пользователя игнорируется
#         https://wiki.termux.com/wiki/Differences_from_Linux
# @exitcode 0 пароль задан
# @exitcode 1 нет
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

# @description Задать автозапуск служб по загрузке Android
# https://wiki.termux.com/wiki/Termux-services
# https://wiki.termux.com/wiki/Termux:Boot
# @exitcode 0 успешно
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

# @description Создать символические ссылки на внутренний и внешний накопитель Android
# https://wiki.termux.com/wiki/Internal_and_external_storage
# https://stackoverflow.com/questions/29789204/bash-how-to-get-real-path-of-a-symlink
# Внутренний накопитель               "${TARGET_DIR_PATH}/android-internal-storage"
#         Внешний накопитель (если доступен)  "${TARGET_DIR_PATH}/android-external-storage"
# @arg $1 string Путь до директории где создавать символические ссылки, необязательный аргумент (если не задано, = текущая директория)
# @exitcode 0 успешно
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

# @set TERMUX_PACKAGE_NAME string Название пакета termux для Android
TERMUX_PACKAGE_NAME="com.termux"

# @set TERMUX_APK_FILE_NAME string Скачиваемый apk termux
TERMUX_APK_FILE_NAME="${TERMUX_PACKAGE_NAME}_1022.apk"

# @description Получить путь до apk termux
# @stdout путь до apk termux
# @exitcode 0 успешно
function termux_get_apk_path() {
    echo "${GLOBAL_CONFIG_OPT_DIR_PATH}/termux/${TERMUX_APK_FILE_NAME}"
    return 0
}

# @description Скачать apk termux
# @arg $1 string Путь для скачивания apk termux, необязательный аргумент (если не задано, = termux_get_apk_path())
# @exitcode 0 успешно
function termux_download_apk() {
    local INSTALL_PATH="${1}"
    if [[ -z "${INSTALL_PATH}" ]]; then
        INSTALL_PATH=$(termux_get_apk_path) || return $?
    fi

    local DOWNLOAD_URL="https://f-droid.org/repo/${TERMUX_APK_FILE_NAME}"
    download_file "${DOWNLOAD_URL}" "${INSTALL_PATH}" "download_if_not_exist" || return $?
    return 0
}
