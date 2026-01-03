FROM alpine:latest

ENV VEIN_SERVER_BACKUP_INTERVAL_SECONDS=3600

RUN apk update && \
    apk add rsync bash findutils coreutils gosu shadow rclone

RUN addgroup -g 1000 vein \
    && adduser -u 1000 -G vein -s /bin/bash -D vein

COPY ./bin/backup_game_data.sh /usr/local/bin/backup_game_data
RUN chmod +x usr/local/bin/backup_game_data

CMD ["/usr/local/bin/backup_game_data"]