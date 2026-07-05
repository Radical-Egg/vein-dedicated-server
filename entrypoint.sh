#!/usr/bin/env bash

set -euo pipefail

PGID="${PGID:-1000}"
PUID="${PUID:-1000}"
VEIN_USER="vein"
VEIN_GROUP="vein"
VEIN_INSTALL_DIR="/home/vein/server"
VEIN_CONFIG_DIR="/home/vein/.config"
VEIN_APP_ID=${VEIN_APP_ID:-2131400}
VEIN_BINARY="${VEIN_INSTALL_DIR}/VeinServer.sh"
VEIN_SERVER_AUTO_UPDATE="${VEIN_SERVER_AUTO_UPDATE:-true}"
VEIN_QUERY_PORT="${VEIN_QUERY_PORT:-27015}"
VEIN_GAME_PORT="${VEIN_GAME_PORT:-7777}"
VEIN_EXTRA_ARGS="${VEIN_EXTRA_ARGS:-}"
VEIN_SERVER_USE_BETA="${VEIN_SERVER_USE_BETA:-false}"
VEIN_SERVER_BETA_BRANCH="${VEIN_SERVER_BETA_BRANCH:-experimental}"
VEIN_SERVER_VALIDATE_INSTALL="${VEIN_SERVER_VALIDATE_INSTALL:-false}"
VEIN_SERVER_ENABLE_HTTP_API="${VEIN_SERVER_ENABLE_HTTP_API:-false}"
VEIN_SERVER_HTTPPORT="${VEIN_SERVER_HTTPPORT:-8080}"
VEIN_SERVER_HTTP_API_HOST="${VEIN_SERVER_HTTP_API_HOST:-127.0.0.1}"
VEIN_SERVER_HTTP_API_TIMEOUT_SECONDS="${VEIN_SERVER_HTTP_API_TIMEOUT_SECONDS:-10}"
VEIN_SERVER_SAVE_AND_EXIT_ON_SHUTDOWN="${VEIN_SERVER_SAVE_AND_EXIT_ON_SHUTDOWN:-true}"
VEIN_SERVER_INSTALL_ARGS=()
VEIN_MANIFEST_DIR="${VEIN_INSTALL_DIR}/steamapps"
VEIN_MANIFEST_NAME="appmanifest_${VEIN_APP_ID}.acf"

if [[ "$#" -gt 0 ]]; then
    exec "$@"
fi

if [[ "${VEIN_SERVER_USE_BETA}" == "true" ]]; then
    echo "Using beta branch: ${VEIN_SERVER_BETA_BRANCH}"
    VEIN_SERVER_INSTALL_ARGS+=(-beta "${VEIN_SERVER_BETA_BRANCH}")
fi

if [[ ! -f "${VEIN_BINARY}" || "${VEIN_SERVER_VALIDATE_INSTALL}" == "true" ]]; then
    echo "Validating install with 'validate' argument"
    VEIN_SERVER_INSTALL_ARGS+=("validate")
fi

warn() {
    echo "WARNING: $*" >&2
}

_TERM() {
    echo "Received shutdown signal..."

    local server_pid="${SERVER_PID:-}"
    if [[ -z "${server_pid}" ]]; then
        echo "No server process has been started yet."
        return
    fi

    if env_bool "${VEIN_SERVER_ENABLE_HTTP_API}" && env_bool "${VEIN_SERVER_SAVE_AND_EXIT_ON_SHUTDOWN}"; then
        echo "Requesting /SaveAndExit from Vein HTTP API..."
        local save_output
        if save_output="$(vein_http_api save-and-exit \
            --host "${VEIN_SERVER_HTTP_API_HOST}" \
            --port "${VEIN_SERVER_HTTPPORT}" \
            --timeout "${VEIN_SERVER_HTTP_API_TIMEOUT_SECONDS}" 2>&1)"; then
            echo "/SaveAndExit request completed. Waiting for server process to exit."
            return
        fi

        if [[ -n "${save_output}" ]]; then
            warn "/SaveAndExit request failed. Falling back to SIGTERM. ${save_output}"
        else
            warn "/SaveAndExit request failed. Falling back to SIGTERM."
        fi
    fi

    echo "Attempting to run kill -TERM ${server_pid} 2>/dev/null"
    kill -TERM "${server_pid}" 2>/dev/null || true
}

env_bool() {
    local val="${1:-}"

    case "${val,,}" in
        true|yes|y|on|1)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

steamcmd_install() {
    gosu "${VEIN_USER}" steamcmd \
        +force_install_dir "${VEIN_INSTALL_DIR}" \
        +login anonymous \
        +app_update "${VEIN_APP_ID}" \
        "${VEIN_SERVER_INSTALL_ARGS[@]}" \
        +quit
}

steamcmd_install_or_update() {
    local log_file
    log_file="$(mktemp)"

    if steamcmd_install 2>&1 | tee "${log_file}"; then
        rm -f "${log_file}"
        return 0
    fi

    echo "SteamCMD update failed. Checking for 0x6 recovery..."

    if grep -Fq "Error! App '${VEIN_APP_ID}' state is 0x6 after update job" "${log_file}"; then
        echo "Detected Steam app state 0x6 for app ${VEIN_APP_ID}. Removing stale manifest and retrying once..."

        if [[ -d "${VEIN_MANIFEST_DIR}" ]]; then
            find "${VEIN_MANIFEST_DIR}" -maxdepth 1 -type f -name "${VEIN_MANIFEST_NAME}" -print -delete
        else
            echo "Manifest directory ${VEIN_MANIFEST_DIR} does not exist yet; skipping delete before retry."
        fi

        if steamcmd_install; then
            rm -f "${log_file}"
            return 0
        fi
    fi

    rm -f "${log_file}"
    return 1
}

# These paths should always be writable
# by VEIN_USER. Iniitally created mounts
# end up being owned by root because the container
# is running as root and using gosu to drop privs
CONFIG_TREE=(
    "${STEAM_HOME}"
    "${VEIN_INSTALL_DIR}"
    "${VEIN_CONFIG_DIR}"
    "${VEIN_CONFIG_DIR}/Epic"
    "${VEIN_CONFIG_DIR}/Epic/Vein"
)

main() {
    if [ "$(id -u "${VEIN_USER}")" != "${PUID}" ]; then
        usermod -o -u "${PUID}" "${VEIN_USER}"
    fi

    if [ "$(getent group "${VEIN_GROUP}" | cut -d: -f3)" != "${PGID}" ]; then
        groupmod -o -g "${PGID}" "${VEIN_GROUP}"
    fi

    for path in "${CONFIG_TREE[@]}"; do
        if [ -e "${path}" ]; then
            if ! gosu "${VEIN_USER}" test -w "${path}"; then
                echo "Permission issue detected for ${path} (not writable by ${VEIN_USER}); fixing..."
                chown -R "${VEIN_USER}:${VEIN_GROUP}" "$path"
            fi
        fi
    done
  
    if [[ ! -f "${VEIN_BINARY}" || "${VEIN_SERVER_AUTO_UPDATE}" == "true" ]]; then
        steamcmd_install_or_update
    fi

    ln -sf "${STEAM_HOME}/steamcmd/linux64/steamclient.so" \
        "${VEIN_INSTALL_DIR}/Vein/Binaries/Linux/steamclient.so"

    echo "Updating Game.ini configs..."
    gosu "${VEIN_USER}" /usr/local/bin/update_config

    echo "Starting Vein server..."

    trap _TERM SIGTERM SIGINT
    exec gosu "${VEIN_USER}" "${VEIN_BINARY}" \
        -log \
        -QueryPort="${VEIN_QUERY_PORT}" \
        -Port="${VEIN_GAME_PORT}" \
        ${VEIN_EXTRA_ARGS:+$VEIN_EXTRA_ARGS}&
    
    SERVER_PID=$!
}

main "$@"

wait "${SERVER_PID}"
