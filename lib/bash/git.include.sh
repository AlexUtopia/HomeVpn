#!/bin/bash

## @brief Функции работы с git

## @brief Клонировать проект (clone) или подтянуть (fetch) последние изменения с перезаписью
## @param [in] URL проекта
## @param [in] Путь до директории проекта
## @param [in] Бранч/тэг
## @retval 0 - успешно
function git_clone_or_fetch() {
    local PROJECT_URL="${1}"
    local PROJECT_DIR_PATH="${2}"
    local PROJECT_BRANCH_OR_TAG="${3}"
    local WORK_BRANCH_NAME=""
    WORK_BRANCH_NAME=$(basename "${PROJECT_BRANCH_OR_TAG}") || return $?
    if [[ -z "${WORK_BRANCH_NAME}" ]]; then
        return 1
    else
        WORK_BRANCH_NAME="work-branch-${WORK_BRANCH_NAME}"
    fi

    if [[ -d "${PROJECT_DIR_PATH}" ]]; then
        pushd "${PROJECT_DIR_PATH}" || return $?
        git fetch &&
        git checkout -f -B "${WORK_BRANCH_NAME}" "${PROJECT_BRANCH_OR_TAG}"
        local COMMAND_CHAIN_RESULT=$?
        popd
        return ${COMMAND_CHAIN_RESULT}
    else
        git clone "${PROJECT_URL}" "${PROJECT_DIR_PATH}" || return $?
        pushd "${PROJECT_DIR_PATH}" || return $?
        git checkout -f -B "${WORK_BRANCH_NAME}" "${PROJECT_BRANCH_OR_TAG}"
        local COMMAND_CHAIN_RESULT=$?
        popd
        return ${COMMAND_CHAIN_RESULT}
    fi
}