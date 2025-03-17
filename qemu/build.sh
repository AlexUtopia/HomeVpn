#!/bin/bash

MY_DIR="$(dirname "$(readlink -f "$0")")"

REQUIRED_ADDITIONAL_PACKAGES="git libglib2.0-dev libfdt-dev libpixman-1-dev zlib1g-dev ninja-build"
RECOMMENDED_ADDITIONAL_PACKAGES="git-email libaio-dev libbluetooth-dev libcapstone-dev libbrlapi-dev libbz2-dev libcap-ng-dev libcurl4-gnutls-dev libgtk-3-dev libibverbs-dev libjpeg8-dev libncurses5-dev libnuma-dev librbd-dev librdmacm-dev libsasl2-dev libsdl2-dev libseccomp-dev libsnappy-dev libssh-dev valgrind xfslibs-dev"

PROJECT_NAME="qemu"
PROJECT_BASE_DIR_PATH="${MY_DIR}"
PROJECT_URL="https://gitlab.com/qemu-project/${PROJECT_NAME}.git"
PROJECT_TAG="v9.2.2"
PROJECT_DIR_PATH="${PROJECT_BASE_DIR_PATH}/${PROJECT_NAME}"
sudo apt update && sudo apt upgrade -o Dpkg::Options::="--force-confnew" -y && sudo apt update && sudo apt -y install ${REQUIRED_ADDITIONAL_PACKAGES} ${RECOMMENDED_ADDITIONAL_PACKAGES} &&
if [[ -d "${PROJECT_DIR_PATH}" ]]; then
    pushd "${PROJECT_DIR_PATH}" &&
    git fetch && git checkout -f -B "tag-branch-${PROJECT_TAG}" "${PROJECT_TAG}" &&
    popd
else
    mkdir -p "${PROJECT_BASE_DIR_PATH}" &&
    pushd "${PROJECT_BASE_DIR_PATH}" &&
    git clone "${PROJECT_URL}" && pushd "${PROJECT_DIR_PATH}" && checkout -f -B "tag-branch-${PROJECT_TAG}" "${PROJECT_TAG}" && popd
    popd
fi

python3 -m pip install "tomli" || exit $?


BUILD_DIR_PATH="${PROJECT_BASE_DIR_PATH}/build" || exit $?

mkdir -p "${BUILD_DIR_PATH}" || exit $?

pushd "${BUILD_DIR_PATH}"

../${PROJECT_NAME}/configure || exit $?
make -j"$(nproc --all)" || exit $?

popd