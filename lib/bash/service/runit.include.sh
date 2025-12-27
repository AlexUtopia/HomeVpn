## @brief Функции работы с runit
## https://smarden.org/runit/
## https://wiki.termux.com/wiki/Termux-services
## https://wiki.termux.com/wiki/Termux:Boot
## https://wiki.gentoo.org/wiki/Runit
## https://docs.voidlinux.org/config/services/index.html


## @brief Получить путь до директории размещения скриптов запуска служб
## @return Путь до директории размещения скриптов запуска системных сервисов
## @retval 0 - успешно
function runit_get_base_dir_path() {
    echo "${SVDIR}"
    return 0
}

## @brief Включить логирование для службы
## @param [in] Имя службы
## @retval 0 - успешно
function runit_create_log_run_file() {
    local SERVICE_NAME="${1}"

    local LOG_RUN_DIR_PATH="$(runit_get_base_dir_path)/${SERVICE_NAME}/log"
    local LOG_RUN_FILE_PATH="${LOG_RUN_DIR_PATH}/run"

    fs_make_dirs "${LOG_RUN_DIR_PATH}" || return $?

    fs_create_symlink "${PREFIX}/share/termux-services/svlogger" "${LOG_RUN_FILE_PATH}" || return $?
    return 0
}

## @brief Создать скрипты запуска службы: run и finish
## @details Примеры скриптов https://smarden.org/runit/runscripts
## @param [in] Имя службы
## @param [in] Содержимое скрипта run
## @param [in] Содержимое скрипта finish
## @retval 0 - успешно
function runit_create_run_file() {
    local SERVICE_NAME="${1}"
    local RUN_FILE_CONTENT="${2}"
    local FINISH_FILE_CONTENT="${3}"

    local SERVICE_DIR_PATH="$(runit_get_base_dir_path)/${SERVICE_NAME}"
    local RUN_FILE_PATH="${SERVICE_DIR_PATH}/run"
    local FINISH_FILE_PATH="${SERVICE_DIR_PATH}/finish"

    fs_create_file "${RUN_FILE_CONTENT}" "${RUN_FILE_PATH}" || return $?
    fs_set_file_as_executable "${RUN_FILE_PATH}" || return $?

    if [[ -n "${FINISH_FILE_CONTENT}" ]]; then
        fs_create_file "${FINISH_FILE_CONTENT}" "${FINISH_FILE_PATH}" || return $?
        fs_set_file_as_executable "${FINISH_FILE_PATH}" || return $?
    fi

    runit_create_log_run_file "${SERVICE_NAME}" || return $?
    return 0
}

## @brief Инициализировать runit
## @retval 0 - успешно
function runit_setup() {
    if is_termux; then
        termux_service_packages_setup || return $?

        # Если не удалось запустить service-daemon то перезагружаем bash и запускаем скрипт setup-packages.sh вновь.
        # После установки termux-services рекомендовано перезапустить termux чтобы bash подхватил новые переменные окружения (нас интересует SVDIR)
        # https://github.com/termux/termux-services/tree/master
        # "Restart your shell so that the service-daemon is started"

        if [[ -z "$(runit_get_base_dir_path)" ]]; then # После установки пакета termux-services в /etc/profile.d/ добавляется скрипт start-services.sh
                                     # который устанавливает требуемые переменные окружения. Перезагрузим (команда exec) bash с полной
                                     # инициализацией и запустим текущий скрипт заново
            echo "RESTART BASH"
            exec ${SHELL} --login -c "${0}" # fixme utopia Надо расследовать циклические перезагрузки скрипта на Android/termux
            # После exec ${SHELL} управление не возвращается
            echo "NEVER"
        fi
        termux_autorun_serves_at_boot || return $?
        return 0
    fi
    return 0
}

## @brief Проверить запущена ли служба
## @param [in] Имя службы
## @retval 0 - служба запущена; 1 - нет
function runit_service_is_active() {
    local SERVICE_NAME="${1}"

    # https://manpages.ubuntu.com/manpages/trusty/en/man8/sv.8.html
    local SERVICE_STATUS=""
    SERVICE_STATUS=$(sv -w 5 status "${SERVICE_NAME}" 2> "/dev/null") || return $?

    if [[ "${SERVICE_STATUS,,}" == "run: "* ]]; then # https://stackoverflow.com/a/229606
        return 0
    fi
    return 1
}

## @brief Добавить службу в автозапуск (при старте ОС) и запустить
## @param [in] Имя службы
## @retval 0 - успешно
function runit_service_enable() {
    local SERVICE_NAME="${1}"

    sv-enable "${SERVICE_NAME}" > "/dev/null"
    if ! $?; then
        sleep 5
        sv-enable "${SERVICE_NAME}" > "/dev/null"
        if ! $?; then
            # Иногда почему-то случается вылет runit и далее служба не может запуститься,
            # поэтому запустим runit заново
            . "${GLOBAL_CONFIG_ETC_DIR_PATH}/profile.d/start-services.sh" > "/dev/null" || return $?
            sleep 5
            sv-enable "${SERVICE_NAME}" > "/dev/null" || return $?
        fi
    fi
    return 0
}

## @brief Остановить службу и убрать её из автозапуска (при старте ОС)
## @param [in] Имя службы
## @retval 0 - успешно
function runit_service_disable() {
    local SERVICE_NAME="${1}"

    sv-disable "${SERVICE_NAME}" > "/dev/null" || return $?
    return 0
}