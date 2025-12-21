

# https://www.gnu.org/software/grep/manual/html_node/Character-Classes-and-Bracket-Expressions.html
function smb_server_get_config_file_path() {
    local SMB_SERVER_BUILD_OPTIONS=""
    SMB_SERVER_BUILD_OPTIONS=$(smbd -b) || return $?

    local REGEX=""
    REGEX=$(printf "CONFIGFILE:[[:blank:]]+([^\n\r]+)") || return $?

    if [[ "${SMB_SERVER_BUILD_OPTIONS}" =~ ${REGEX} ]]; then
        echo "${BASH_REMATCH[1]}"
        return 0
    fi

    return 1
}