#!/usr/bin/env bash

set -euo pipefail

PGID="${PGID:-1000}"
PUID="${PUID:-1000}"
VEIN_USER="vein"
VEIN_GROUP="vein"
VEIN_SERVER_BACKUP_SRC_DIR=${VEIN_SERVER_BACKUP_SRC_DIR:-/data}
VEIN_SERVER_BACKUP_DIR=${VEIN_SERVER_BACKUP_DIR:-/backup}
VEIN_SERVER_BACKUP_RETENTION=${VEIN_SERVER_BACKUP_RETENTION:-5}
VEIN_SERVER_BACKUP_MODE=${VEIN_SERVER_BACKUP_MODE:-rsync}
VEIN_SERVER_BACKUP_S3_BUCKET=${VEIN_SERVER_BACKUP_S3_BUCKET:-backups}

INTERVAL="${VEIN_SERVER_BACKUP_INTERVAL_SECONDS:-3600}"

RCLONE_CONTIMEOUT=${VEIN_SERVER_BACKUP_S3_CONNTIMEOUT:-5s}
RCLONE_TIMEOUT=${VEIN_SERVER_BACKUP_S3_TIMEOUT:-30s}
RCLONE_RETRIES=${VEIN_SERVER_BACKUP_S3_RETRIES:-2}

RCLONE_CONFIG_VS3_ENDPOINT=${VEIN_SERVER_BACKUP_S3_ENDPOINT:-}
RCLONE_CONFIG_VS3_TYPE=${VEIN_SERVER_BACKUP_S3_TYPE:-s3}
RCLONE_CONFIG_VS3_PROVIDER=${VEIN_SERVER_BACKUP_S3_PROVIDER:-Other}
RCLONE_CONFIG_VS3_REGION=${VEIN_SERVER_BACKUP_S3_REGION:-garage}
RCLONE_CONFIG_VS3_ACCESS_KEY_ID=${VEIN_SERVER_BACKUP_S3_KEY_ID:-}
RCLONE_CONFIG_VS3_SECRET_ACCESS_KEY=${VEIN_SERVER_BACKUP_S3_ACCESS_KEY:-}

export PGID PUID VEIN_USER VEIN_GROUP \
       VEIN_SERVER_BACKUP_SRC_DIR VEIN_SERVER_BACKUP_DIR \
       VEIN_SERVER_BACKUP_RETENTION INTERVAL VEIN_SERVER_BACKUP_MODE \
       VEIN_SERVER_BACKUP_S3_BUCKET RCLONE_CONTIMEOUT RCLONE_TIMEOUT RCLONE_RETRIES \
       RCLONE_CONFIG_VS3_ENDPOINT RCLONE_CONFIG_VS3_TYPE RCLONE_CONFIG_VS3_PROVIDER \
       RCLONE_CONFIG_VS3_REGION RCLONE_CONFIG_VS3_ACCESS_KEY_ID RCLONE_CONFIG_VS3_SECRET_ACCESS_KEY

SLEEP_PID=""
on_exit() {
    echo "[backup] Caught shutdown signal. Exiting..."
    if [[ -n "${SLEEP_PID}" ]] && kill -0 "${SLEEP_PID}" 2>/dev/null; then
        kill "${SLEEP_PID}" 2>/dev/null || true
    fi
    exit 0
}

trap on_exit TERM int

main() {
    case $VEIN_SERVER_BACKUP_MODE in
        "rsync")
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
            ;;
        "s3")
            mkdir -p "${HOME}/.config/rclone/"
            touch "${HOME}/.config/rclone/rclone.conf"

            TS="$(date -u +%Y%m%dT%H%M%SZ)"
            BACKUP_DIR=$(date -u +%d%b%Y | tr '[':lower:']' '[:upper:]')
            echo "Sending Server.vns to S3 endpoint to ${RCLONE_CONFIG_VS3_ENDPOINT}"
            find "${VEIN_SERVER_BACKUP_SRC_DIR}" \
                -type f \
                -name "Server.vns" \
                -exec rclone copy {} "vs3:${VEIN_SERVER_BACKUP_S3_BUCKET}/vein-server/current/" \
                --backup-dir "vs3:${VEIN_SERVER_BACKUP_S3_BUCKET}/vein-server/versions/${BACKUP_DIR}" \
                --suffix ".${TS}" \;

            echo "Sending Game.ini to S3 to ${RCLONE_CONFIG_VS3_ENDPOINT}"
            find "${VEIN_SERVER_BACKUP_SRC_DIR}" \
                -type f \
                -name "Game.ini" \
                -exec rclone copy {} "vs3:${VEIN_SERVER_BACKUP_S3_BUCKET}/vein-server/current/" \
                --backup-dir "vs3:${VEIN_SERVER_BACKUP_S3_BUCKET}/vein-server/versions/${BACKUP_DIR}" \
                --suffix ".${TS}" \;
            ;;
        *)
            echo "Unknown backup mode: ${VEIN_SERVER_BACKUP_MODE}"
            ;;
    esac
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
    sleep "${INTERVAL}" &
    SLEEP_PID=$!
    
    wait "${SLEEP_PID}" || true
    SLEEP_PID=""
done
