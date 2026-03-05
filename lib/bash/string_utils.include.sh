#!/bin/bash

## @brief Функции по работе со строками


## @brief Повторить строку N раз
## @param [in] Строка-образец для повторения
## @param [in] Количество повторений, если не задан, функция вернёт пустую строку
## @return Строка-образец повторённая N раз
## @retval 0 - успешно
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
