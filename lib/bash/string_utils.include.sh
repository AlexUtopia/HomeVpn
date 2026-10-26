#!/bin/bash

# @file string_utils.include.sh
# @brief Функции по работе со строками


# @description Повторить строку N раз
# @arg $1 string Строка-образец для повторения
# @arg $2 string Количество повторений, если не задан, функция вернёт пустую строку
# @stdout Строка-образец повторённая N раз
# @exitcode 0 успешно
function str_repeat() {
    local STR_FOR_REPEAT="${1}"
    local REPEAT_COUNT="${2}"

    local RESULT=""
    for (( i=0; i<REPEAT_COUNT; i++ )); do
        RESULT="${RESULT}${STR_FOR_REPEAT}"
    done
    echo "${RESULT}"
    return 0
}
