#!/usr/bin/env bash

set -euo pipefail

PGID="${PGID:-1000}"
PUID="${PUID:-1000}"
VEIN_USER="vein"
VEIN_GROUP="vein"
VEIN_SERVER_BACKUP_SRC_DIR=${VEIN_SERVER_BACKUP_SRC_DIR:-/data}
VEIN_SERVER_BACKUP_DIR=${VEIN_SERVER_BACKUP_DIR:-/backup}
VEIN_SERVER_BACKUP_RETENTION=${VEIN_SERVER_BACKUP_RETENTION:-5}
INTERVAL="${VEIN_SERVER_BACKUP_INTERVAL_SECONDS:-3600}"

export PGID PUID VEIN_USER VEIN_GROUP \
       VEIN_SERVER_BACKUP_SRC_DIR VEIN_SERVER_BACKUP_DIR \
       VEIN_SERVER_BACKUP_RETENTION INTERVAL

main() {
    now="$(date +%Y-%m-%d_%H%M%S).backup"
    mkdir -p "${VEIN_SERVER_BACKUP_DIR}/${now}"

    echo "[backup] Starting backup..."
    find "${VEIN_SERVER_BACKUP_SRC_DIR}" \
        -type d \
        -name "Saved" \
        -exec rsync -a "{}" "${VEIN_SERVER_BACKUP_DIR}/${now}" \;

    echo "[backup] Backup complete.. attempting to remove old backups"
    if (( VEIN_SERVER_BACKUP_RETENTION > 0 )); then
        START=$((VEIN_SERVER_BACKUP_RETENTION + 1 ))

        ls -1dt -- "$VEIN_SERVER_BACKUP_DIR"/*/ \
            | grep -E '\.backup/?$' \
            | tail -n +"$START" \
            | xargs -r rm -rf
    fi
    echo "[backup] Old backups have been removed"
}

while true; do
    if [ "$(id -u "${VEIN_USER}")" != "${PUID}" ]; then
        usermod -o -u "${PUID}" "${VEIN_USER}"
    fi

    if [ "$(getent group "${VEIN_GROUP}" | cut -d: -f3)" != "${PGID}" ]; then
        groupmod -o -g "${PGID}" "${VEIN_GROUP}"
    fi

    if [ "$(stat -c %u "${VEIN_SERVER_BACKUP_DIR}")" != "${PUID}" ]; then
        echo "Adjusting permissions for ${VEIN_SERVER_BACKUP_DIR}.."
        chown -R "${VEIN_USER}:${VEIN_GROUP}" "${VEIN_SERVER_BACKUP_DIR}"
    fi

    gosu "${VEIN_USER}" bash -c "$(declare -f main); main"
    echo "[backup] Sleeping for $INTERVAL"
    sleep "${INTERVAL}"
done
