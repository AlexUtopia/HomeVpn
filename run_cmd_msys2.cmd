chcp 65001
@echo off
:: Скрипт который предоставляет вызов функции из целевого окружения,
:: шарится между batch и python чтобы не плодить копипасту

set "MSYS2_INSTALL_DIR_PATH=%SYSTEMDRIVE%:\msys64"
set "MSYS2_CONSOLE=%MSYS2_INSTALL_DIR_PATH%\msys2_shell.cmd"
set "HOME_VPN_PROJECT_ROOT=%~dp0"

call "%MSYS2_CONSOLE%" -no-start -clang64 -defterm -c "%HOME_VPN_PROJECT_ROOT%\run_cmd.sh %*"