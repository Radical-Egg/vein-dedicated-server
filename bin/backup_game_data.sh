#!/usr/bin/env bash

set -euo pipefail

VEIN_SERVER_BACKUP_SRC_DIR=${VEIN_SERVER_BACKUP_SRC_DIR:-/data}
VEIN_SERVER_BACKUP_DIR=${VEIN_SERVER_BACKUP_DIR:-/backup}
VEIN_SERVER_BACKUP_RETENTION=${VEIN_SERVER_BACKUP_RETENTION:-5}
INTERVAL="${VEIN_SERVER_BACKUP_INTERVAL_SECONDS:-3600}"

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
    main
    echo "[backup] Sleeping for $INTERVAL"
    sleep "${INTERVAL}"
done
