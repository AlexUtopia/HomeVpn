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
    return 1
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