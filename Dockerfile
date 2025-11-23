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
    zlib1g && \
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
RUN chmod +x /entrypoint.sh

ENTRYPOINT [ "/bin/bash", "/entrypoint.sh" ]