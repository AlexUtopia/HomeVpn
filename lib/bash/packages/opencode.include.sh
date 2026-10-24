#!/bin/bash

## @brief Функции по установке opencode
## @details AI агент используемый для создания проекта HomeVpn
## https://opencode.ai/v2/docs/


## @brief Установить пакет opencode
## @retval 0 - успешно
function opencode_packages_setup() {
    local DOWNLOAD_URL="https://opencode.ai/v2/install"

    download_file "${DOWNLOAD_URL}" "-" | "${SHELL}" || return $?
    return 0
}

## @brief Установить LSP (Language Server Protocol) для opencode
## @details Для языков используемых в проекте: python, bash
## @retval 0 - успешно
function opencode_setup_lsp() {
    # Cм. https://opencode.ai/docs/lsp/
    return 0
}

## @brief Установить и настроить opencode
## @retval 0 - успешно
function opencode_setup() {
    opencode_packages_setup || return $?
    opencode_setup_lsp || return $?
    return 0
}
