chcp 65001
rem @echo off

rem Использование bitsadmin для скачивания файлов https://xakep.ru/2015/09/14/easy-hack-200/
rem Установка msys2 из командной строки https://github.com/msys2/msys2-installer?tab=readme-ov-file#cli-usage-examples
rem Запуск команды msys2 на исполнение из под cmd https://www.msys2.org/wiki/Launchers/


set "PROJECT_NAME=HomeVpn"
set "MSYS2_DOWNLOAD_URL=https://github.com/msys2/msys2-installer/releases/download/2024-07-27/msys2-x86_64-20240727.exe"
set "MSYS2_INSTALLER_FILE_PATH=%PUBLIC%\Downloads\msys2-x86_64.exe"
set "MSYS2_INSTALL_DIR_PATH=C:\msys64"
set "MSYS2_CONSOLE=%MSYS2_INSTALL_DIR_PATH%\msys2_shell.cmd"


rem 1) Скачаем msys2
bitsadmin /transfer download_msys2_job /download "%MSYS2_DOWNLOAD_URL%" "%MSYS2_INSTALLER_FILE_PATH%"
if %ERRORLEVEL% NEQ 0 (
    echo Download MSYS2 FAIL: %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)
echo Download MSYS2 OK


rem 2) Установим msys2
"%MSYS2_INSTALLER_FILE_PATH%" install --verbose --confirm-command --accept-messages --root "%MSYS2_INSTALL_DIR_PATH%"
if %ERRORLEVEL% EQU 0 (
    echo Install MSYS2 OK
) else if %ERRORLEVEL% EQU 1 (
    echo MSYS2 already installed
) else (
    echo Install MSYS2 FAIL: %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)

rem 3) Скачаем и настроим HomeVpn
call "%MSYS2_CONSOLE%" -no-start -clang64 -defterm -c ^"set -x; PROJECT_BASE_DIR_PATH=$(echo ~); ^
PROJECT_NAME=^"%PROJECT_NAME%^"; ^
PROJECT_URL=^"https://github.com/AlexUtopia/${PROJECT_NAME}.git^"; ^
PROJECT_BRANCH=^"main^"; ^
PROJECT_DIR_PATH=^"${PROJECT_BASE_DIR_PATH}/${PROJECT_NAME}^"; ^
RUN_WITH_ADMIN_RIGHTS=; ^
RUN_WITH_ADMIN_RIGHTS_PRESERV_ENV=; ^
${RUN_WITH_ADMIN_RIGHTS} pacman -Syu --noconfirm ^&^& pacman -S --noconfirm git ^&^& ^
if [[ -d ^"${PROJECT_DIR_PATH}^" ]]; then ^
    pushd ^"${PROJECT_DIR_PATH}^" ^&^& ^
    git fetch ^&^& git checkout -f -B ^"${PROJECT_BRANCH}^" ^"remotes/origin/${PROJECT_BRANCH}^"; ^
    ${RUN_WITH_ADMIN_RIGHTS_PRESERV_ENV} ^"${PROJECT_DIR_PATH}/setup-packages.sh^"; ^
    popd; ^
else ^
    mkdir -p ^"${PROJECT_BASE_DIR_PATH}^" ^&^& ^
    pushd ^"${PROJECT_BASE_DIR_PATH}^" ^&^& ^
    git clone ^"${PROJECT_URL}^" -b ^"${PROJECT_BRANCH}^"; ^
    ${RUN_WITH_ADMIN_RIGHTS_PRESERV_ENV} ^"${PROJECT_DIR_PATH}/setup-packages.sh^"; ^
    popd; ^
fi"
if %ERRORLEVEL% NEQ 0 (
    echo Setup %PROJECT_NAME% FAIL: %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)
echo Setup %PROJECT_NAME% OK
