FROM alpine:latest

RUN apk update && \
    apk add rsync bash findutils coreutils

ENV VEIN_SERVER_BACKUP_INTERVAL_SECONDS=3600

COPY ./bin/backup_game_data.sh /usr/local/bin/backup_game_data
RUN chmod +x usr/local/bin/backup_game_data

CMD ["/usr/local/bin/backup_game_data"]