#!/bin/bash

# @file opencode.include.sh
# @brief Функции по установке opencode
# @description
# AI агент используемый для создания проекта HomeVpn
# https://opencode.ai/v2/docs/


# @description Установить пакет opencode
# @exitcode 0 успешно
function opencode_packages_setup() {
    local DOWNLOAD_URL="https://opencode.ai/v2/install"

    download_file "${DOWNLOAD_URL}" "-" | "${SHELL}" || return $?
    return 0
}

# @description Установить LSP (Language Server Protocol) для opencode
# Для языков используемых в проекте: python, bash
# @exitcode 0 успешно
function opencode_setup_lsp() {
    # Cм. https://opencode.ai/docs/lsp/
    return 0
}

# @description Установить и настроить opencode
# @exitcode 0 успешно
function opencode_setup() {
    opencode_packages_setup || return $?
    opencode_setup_lsp || return $?
    return 0
}
