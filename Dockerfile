FROM steamcmd/steamcmd:debian

RUN apt-get update && \
    apt-get install -y gosu \
    lib32gcc-s1 \
    lib32stdc++6 \
    libstdc++6 \
    libgcc-s1 \
    libc6 \
    libcurl4 \
    libssl3 \
    libatomic1 \
    libuuid1 \
    libicu76 \
    libasound2 \
    libpulse0 \
    zlib1g \
    python3 && \
    rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1000 vein \
    && useradd -u 1000 -g vein -m -s /bin/bash vein

WORKDIR /home/vein
ENV HOME=/home/vein
ENV XDG_DATA_HOME="${HOME}/.local/share"
ENV STEAM_HOME="${XDG_DATA_HOME}/Steam"

USER vein
RUN steamcmd +login anonymous +quit

RUN mkdir -p /home/vein/server

USER root

EXPOSE 27015/udp
EXPOSE 7777/udp

COPY --chown=vein:vein entrypoint.sh /entrypoint.sh
COPY --chown=vein:vein ./bin/update_config.py /usr/local/bin/update_config
COPY --chown=vein:vein ./bin/healthcheck.py /usr/local/bin/healthcheck

RUN chmod +x /entrypoint.sh && \
    chmod +x /usr/local/bin/update_config && \
    chmod +x /usr/local/bin/healthcheck

HEALTHCHECK --interval=30s \
    --start-period=60s \
    --start-interval=10s \
    --timeout=10s \
    --retries=10 \
    CMD /usr/local/bin/healthcheck

ENTRYPOINT [ "/bin/bash", "/entrypoint.sh" ]
