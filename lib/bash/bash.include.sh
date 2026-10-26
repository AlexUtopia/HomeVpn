#!/bin/bash

# @file bash.include.sh
# @brief Функции интерпретатора bash
# @description
# Руководство по регулярным выражениям в bash (POSIX-ExtendedRegularExpressions)
#          https://www.gnu.org/software/bash/manual/bash.html#Pattern-Matching-1
#          https://en.wikibooks.org/wiki/Regular_Expressions/POSIX-Extended_Regular_Expressions


# @description Получить путь до исполняемого файла
# https://stackoverflow.com/a/26759734
# @arg $1 string Имя исполняемого файла, можно с полным путём до исполняемого файла
# @exitcode 0 успешно
function get_executable_path() {
    local EXECUTABLE_OR_PATH="${1}"

    command -v "${EXECUTABLE_OR_PATH}" || return $?
    return 0
}

# @description Проверить существует ли целевой исполняемый файл
# https://stackoverflow.com/a/26759734
# @arg $1 string Имя исполняемого файла, можно с полным путём до исполняемого файла
# @exitcode 0 если целевой исполняемый файл существует
# @exitcode 1 не существует
function is_executable_available() {
    local EXECUTABLE_OR_PATH="${1}"

    local TARGET_EXECUTABLE_PATH=""
    TARGET_EXECUTABLE_PATH=$(get_executable_path "${EXECUTABLE_OR_PATH}" 2> "/dev/null") || return $?
    if [[ -x "${TARGET_EXECUTABLE_PATH}" ]]; then
        return 0
    fi
    return 1
}

# @description Проверить результат выполнения функции на успех
# Использовать с оператором if, пример
#
#         target_function_call
#         local TARGET_FUNCTION_RESULT=$?
#         if [[ ! check_return_code ${TARGET_FUNCTION_RESULT} ]]; then
#             # Обработать неуспешное исполнение target_function_call
#             return ${TARGET_FUNCTION_RESULT}
#         else
#             # Обработать успешное исполнение target_function_call
#         fi
#
# @arg $1 string Результат выполнения целевой функции
# @exitcode ${1} Результат выполнения целевой функции пригодный для использования с оператором if
function check_return_code() {
    return ${1}
}

# @set TRAP_TABLE assoc array Глобальный словарь обработчиков событий. Ключ: "<название события>|<текущий shell/subshell PID>" Значение: обработчики события в LIFO порядке. Функция trap перетирает уже заданный обработчик, требуется обойти данное поведение
declare -A TRAP_TABLE

# @description Установить обработчик события (trap)
# https://www.gnu.org/software/bash/manual/bash.html#index-trap
# @arg $1 string Обработчик события в виде строки
# @arg $2 string Имя события
# @exitcode 0 успешно
function trap_add_handler() {
    local TRAP_HANDLER="${1}"
    local TRAP_SIGNAL="${2}"

    local TRAP_TABLE_KEY="${TRAP_SIGNAL}|${BASHPID}"

    local CURRENT_TRAP_HANDLER_CHAIN=${TRAP_TABLE["${TRAP_TABLE_KEY}"]}
    local NEW_TRAP_HANDLER_CHAIN="${TRAP_HANDLER}"
    if [[ -n "${CURRENT_TRAP_HANDLER_CHAIN}" ]]; then
        NEW_TRAP_HANDLER_CHAIN="${TRAP_HANDLER}; ${CURRENT_TRAP_HANDLER_CHAIN}"
    fi
    TRAP_TABLE["${TRAP_TABLE_KEY}"]="${NEW_TRAP_HANDLER_CHAIN}"
    echo "[trap] add for ${TRAP_TABLE_KEY}: ${NEW_TRAP_HANDLER_CHAIN}"

    trap "${NEW_TRAP_HANDLER_CHAIN}" "${TRAP_SIGNAL}"
    return 0
}

# @description Установить обработчик удаления временного файла или директории
# @arg $1 string Путь до удаляемого временного файла или директории
# @exitcode 0 успешно
function trap_add_remove_temp_path_handler() {
    local TEMP_FILE_OR_DIR_PATH="${1}"

    local TRAP_HANDLER="rm -fr '${TEMP_FILE_OR_DIR_PATH}'"

    trap_add_handler "${TRAP_HANDLER}" SIGINT
    trap_add_handler "${TRAP_HANDLER}" EXIT
    return 0
}

# @description Установить обработчик завершения job'a
# Вызывать функцию сразу после запуска job'a
# Обработчик устанавливается на сигнал SIGINT и завершение shell/subshell процесса
#         с ожиданием завершения (wait <job PID>)
# @arg $1 string Имя job'a (для отладки)
# @arg $2 string Обработчик завершения job'a в виде строки, необязательный аргумент (если не задано, = kill -SIGTERM <job PID>)
# @exitcode 0 успешно
function job_setup_kill_handler() {
    JOB_NAME="${1}"
    KILL_JOB_HANDLER="${2}"

    JOB_PID="$!"
    if [[ -z "${KILL_JOB_HANDLER}" ]]; then
        KILL_JOB_HANDLER="kill -SIGTERM ${JOB_PID}"
    fi

    local TRAP_HANDLER="${KILL_JOB_HANDLER}; wait ${JOB_PID}"
    local TRAP_HANDLER_WITH_ECHO="echo '[${JOB_NAME}] ${TRAP_HANDLER}'; ${TRAP_HANDLER}"

    trap_add_handler "${TRAP_HANDLER_WITH_ECHO}" SIGINT
    trap_add_handler "${TRAP_HANDLER_WITH_ECHO}" EXIT
    return 0
}
