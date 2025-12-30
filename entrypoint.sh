#!/usr/bin/env bash

set -euo pipefail

PGID="${PGID:-1000}"
PUID="${PUID:-1000}"
VEIN_USER="vein"
VEIN_GROUP="vein"
VEIN_INSTALL_DIR="/home/vein/server"
VEIN_APP_ID=${VEIN_APP_ID:-2131400}
VEIN_BINARY="${VEIN_INSTALL_DIR}/VeinServer.sh"
VEIN_SERVER_AUTO_UPDATE="${VEIN_SERVER_AUTO_UPDATE:-true}"
VEIN_QUERY_PORT="${VEIN_QUERY_PORT:-27015}"
VEIN_GAME_PORT="${VEIN_GAME_PORT:-7777}"
VEIN_EXTRA_ARGS="${VEIN_EXTRA_ARGS:-}"
VEIN_SERVER_USE_BETA="${VEIN_SERVER_USE_BETA:-false}"
VEIN_SERVER_BETA_BRANCH="${VEIN_SERVER_BETA_BRANCH:-experimental}"
VEIN_SERVER_INSTALL_ARGS=()

if [[ "${VEIN_SERVER_USE_BETA}" == "true" ]]; then
    VEIN_SERVER_INSTALL_ARGS+=(-beta "${VEIN_SERVER_BETA_BRANCH}")
fi

_TERM() { 
    echo "Received shutdown signal..."
    echo "Attempting to run kill -TERM ${SERVER_PID} 2>/dev/null"
    kill -TERM "${SERVER_PID}" 2>/dev/null;     
}

main() {
    if [ "$(id -u "${VEIN_USER}")" != "${PUID}" ]; then
        usermod -o -u "${PUID}" "${VEIN_USER}"
    fi

    if [ "$(getent group "${VEIN_GROUP}" | cut -d: -f3)" != "${PGID}" ]; then
        groupmod -o -g "${PGID}" "${VEIN_GROUP}"
    fi

    if [ "$(stat -c %u "${STEAM_HOME}")" != "${PUID}" ]; then
        echo "Fixing permissions on ${STEAM_HOME}"
        chown -R "${VEIN_USER}:${VEIN_GROUP}" "${STEAM_HOME}"
    fi

    if [ "$(stat -c %u "${VEIN_INSTALL_DIR}")" != "${PUID}" ]; then
        echo "Adjusting permissions for ${VEIN_INSTALL_DIR}.."
        chown -R "${VEIN_USER}:${VEIN_GROUP}" "${VEIN_INSTALL_DIR}"
    fi

    if [[ ! -f "${VEIN_BINARY}" || "${VEIN_SERVER_AUTO_UPDATE}" == "true" ]]; then
        gosu "${VEIN_USER}" steamcmd \
            +force_install_dir "${VEIN_INSTALL_DIR}" \
            +login anonymous \
            +app_update "${VEIN_APP_ID}" \
            "${VEIN_SERVER_INSTALL_ARGS[@]}" validate \
            +quit
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
