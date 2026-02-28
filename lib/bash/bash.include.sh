#!/bin/bash

## @brief Функции интерпретатора bash
## @details Руководство по регулярным выражениям в bash (POSIX-ExtendedRegularExpressions)
##          https://www.gnu.org/software/bash/manual/bash.html#Pattern-Matching-1
##          https://en.wikibooks.org/wiki/Regular_Expressions/POSIX-Extended_Regular_Expressions


## @brief Получить путь до исполняемого файла
## @details https://stackoverflow.com/a/26759734
## @param [in] Имя исполняемого файла, можно с полным путём до исполняемого файла
## @retval 0 - успешно
function get_executable_path() {
    local EXECUTABLE_OR_PATH="${1}"

    command -v "${EXECUTABLE_OR_PATH}" || return $?
    return 0
}

## @brief Проверить существует ли целевой исполняемый файл
## @details https://stackoverflow.com/a/26759734
## @param [in] Имя исполняемого файла, можно с полным путём до исполняемого файла
## @retval 0 - если целевой исполняемый файл существует; 1 - не существует
function is_executable_available() {
    local EXECUTABLE_OR_PATH="${1}"

    local TARGET_EXECUTABLE_PATH=""
    TARGET_EXECUTABLE_PATH=$(get_executable_path "${EXECUTABLE_OR_PATH}" 2> "/dev/null") || return $?
    if [[ -x "${TARGET_EXECUTABLE_PATH}" ]]; then
        return 0
    fi
    return 1
}

## @brief Проверить результат выполнения функции на успех
## @details Использовать с оператором if, пример
##
##          target_function_call
##          local TARGET_FUNCTION_RESULT=$?
##          if [[ ! check_return_code ${TARGET_FUNCTION_RESULT} ]]; then
##              # Обработать неуспешное исполнение target_function_call
##              return ${TARGET_FUNCTION_RESULT}
##          else
##              # Обработать успешное исполнение target_function_call
##          fi
##
## @param [in] Результат выполнения целевой функции
## @retval Результат выполнения целевой функции пригодный для использования с оператором if
function check_return_code() {
    return ${1}
}

declare -A TRAP_TABLE

# https://www.gnu.org/software/bash/manual/bash.html#index-trap
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
