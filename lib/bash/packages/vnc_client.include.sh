#!/bin/bash

## @brief Функции работы с клиентом VNC


## @brief Установить VNC клиент
## @details https://tigervnc.org/
## @retval 0 - успешно
function vnc_client_setup() {
    if is_msys; then
        local TIGER_VNC_VERSION="1.15.0"
        local TIGER_VNC_INSTALLER="tigervnc64-${TIGER_VNC_VERSION}.exe"
        local DOWNLOAD_FILE_PATH="${GLOBAL_CONFIG_OPT_DIR_PATH}/${TIGER_VNC_INSTALLER}"
        local DOWNLOAD_URL="https://altushost-swe.dl.sourceforge.net/project/tigervnc/stable/${TIGER_VNC_VERSION}/${TIGER_VNC_INSTALLER}"
        download_file "${DOWNLOAD_URL}" "${DOWNLOAD_FILE_PATH}" || return $?
        # fixme utopia Заинсталировать приложение ${DOWNLOAD_FILE_PATH}
        #              Использовать специальный менеджер пакетов
        return 0
    fi

    package_manager_install_packages "tigervnc-viewer" || return $?
    return 0
}