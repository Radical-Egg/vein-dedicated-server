FROM alpine:latest

ENV VEIN_SERVER_BACKUP_INTERVAL_SECONDS=3600 \
    VEIN_SERVER_HTTP_API_HOST=vein \
    VEIN_SERVER_HTTPPORT=8080

RUN apk update && \
    apk add rsync bash findutils coreutils gosu shadow rclone python3 py3-requests

RUN addgroup -g 1000 vein \
    && adduser -u 1000 -G vein -s /bin/bash -D vein

RUN mkdir /data

COPY ./bin/backup_game_data.sh /usr/local/bin/backup_game_data
COPY ./bin/vein_http_api.py /usr/local/bin/vein_http_api
RUN chmod +x /usr/local/bin/backup_game_data && \
    chmod +x /usr/local/bin/vein_http_api

CMD ["/usr/local/bin/backup_game_data"]
