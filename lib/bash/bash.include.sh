#!/bin/bash

## @brief Функции интерпретатора bash


## @brief Проверить существует ли целевой исполняемый файл
## @details https://stackoverflow.com/a/26759734
## @param [in] Имя исполняемого файла, можно с полным путём до исполняемого файла
## @retval 0 если целевой исполняемый файл существует; 1 - не существует
function is_executable_available() {
    local EXECUTABLE_OR_PATH="${1}"

    local TARGET_EXECUTABLE_PATH
    TARGET_EXECUTABLE_PATH=$(command -v "${EXECUTABLE_OR_PATH}") || return $?
    if [[ -x "${TARGET_EXECUTABLE_PATH}" ]]; then
        return 0
    fi
    return 1
}