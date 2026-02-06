# VEIN Dedicated Server Docker Image
[![Release](https://img.shields.io/github/v/release/Radical-Egg/vein-dedicated-server?display_name=tag&sort=semver)](https://github.com/Radical-Egg/vein-dedicated-server/releases)
[![License](https://img.shields.io/github/license/Radical-Egg/vein-dedicated-server)](./LICENSE)
[![Stars](https://img.shields.io/github/stars/Radical-Egg/vein-dedicated-server?style=flat)](https://github.com/Radical-Egg/vein-dedicated-server/stargazers)
[![Issues](https://img.shields.io/github/issues/Radical-Egg/vein-dedicated-server)](https://github.com/Radical-Egg/vein-dedicated-server/issues)
[![Release](https://github.com/Radical-Egg/vein-dedicated-server/actions/workflows/publish-ghcr.yml/badge.svg)](https://github.com/Radical-Egg/vein-dedicated-server/actions/workflows/publish-ghcr.yml)

Run a **VEIN dedicated server** with **Docker Compose** — optional **automatic updates**, **HTTP API**, and **scheduled backups** (local rsync or S3 via rclone).

✅ Fast setup (copy/paste compose)  
✅ Persistent saves/config via volumes  
✅ Backups (local or S3)  
✅ Optional Helm chart for Kubernetes

> This project is **unofficial** and not affiliated with the VEIN developers or Valve.

## Table of contents
- [Quickstart](#quickstart-docker-compose)
- [Backups](#backups)
  - [Local backups](#local-backups-rsync)
  - [S3 backups](#s3-backups-rclone)
- [Kubernetes (Helm)](#kubernetes-helm)
- [Configuration](#environment-variables)
- [Licensing](#licensing)

## QuickStart (Docker Compose)

Below is an example setup using Docker compose and local backups. Local backups will rsync your save and configuration files to the `./backup` directory mounted to the sidecar container. See the backups section for more details.

```yaml
services:
  vein:
    image: ghcr.io/radical-egg/vein-dedicated-server:latest
    container_name: vein-dedicated-server
    restart: unless-stopped
    ports:
      - "27015:27015/udp" # Steam Query Port
      - "7777:7777/udp" # Game Port
      - "8080:8080/tcp" # HTTP API Port
    volumes:
      - ./data:/home/vein/server # game data and configs like Game.ini Engine.ini
      - ./config:/home/vein/.config/Epic/Vein # Experimental branches store save files here
    environment:
      TZ: America/Los_Angeles
      PUID: 1000 # replace with your users UID
      PGID: 1000 # replace with your users GID
      VEIN_SERVER_AUTO_UPDATE: true
      VEIN_SERVER_NAME: "Vein2Docker"
      VEIN_SERVER_DESCRIPTION: '"Vein Dedicated Server using docker"'
      VEIN_SERVER_PASSWORD: "secret"
      VEIN_SERVER_ENABLE_HTTP_API: true
#      VEIN_SERVER_USE_BETA: true
#      VEIN_SERVER_ADMIN_STEAM_IDS: "12345,12345,12345562312"
#      VEIN_SERVER_SUPER_ADMIN_STEAM_IDS: "12345"
  vein-backup-sidecar:
    image: ghcr.io/radical-egg/vein-dedicated-backup:latest
    container_name: vein-dedicated-backup
    volumes:
      - ./data:/data/vein-data:ro
      - ./config:/data/vein-config:ro
      - ./backup:/backup:rw
    environment:
      PUID: 1000 # replace with your users UID
      PGID: 1000 # replace with your users GID
      VEIN_SERVER_BACKUP_INTERVAL_SECONDS: 7200
      VEIN_SERVER_BACKUP_RETENTION: 10 # set to 0 to keep all backups
```

## Backups

### Local Backups (Rsync)

You can use this sidecar container to backup your game saves (Server.vns) and configuration files to a directory mount that you specify in the compose config. It is important to note that the backup container will look for files in `/data` so I recommend using `/data/vein-data` and `/data/vein-config` like the example below.

```yaml
services:
  vein-backup-sidecar:
    image: ghcr.io/radical-egg/vein-dedicated-backup:latest
    container_name: vein-dedicated-backup
    volumes:
      - ./data:/data/vein-data:ro
      - ./config:/data/vein-config:ro
      - ./backup:/backup:rw
    environment:
      PUID: 1000 # replace with your users UID
      PGID: 1000 # replace with your users GID
      VEIN_SERVER_BACKUP_INTERVAL_SECONDS: 7200
      VEIN_SERVER_BACKUP_RETENTION: 10 # set to 0 to keep all backups
```

### S3 Backups (Rclone)

The backup container has Rclone installed and can be used to send a backup of your Server.vns and
Game.ini to and S3 bucket. The example configurations below are what I use for my self hosted Garage S3 instance.

```yaml
services:
  vein-backup-sidecar:
    image: ghcr.io/radical-egg/vein-dedicated-backup:latest
    container_name: vein-dedicated-backup
    volumes:
      - ./data:/data/vein-data:ro
      - ./config:/data/vein-config:ro
      - ./backup:/backup:rw
    environment:
      PUID: 1000 # replace with your users UID
      PGID: 1000 # replace with your users GID
      VEIN_SERVER_BACKUP_INTERVAL_SECONDS: 7200
      VEIN_SERVER_BACKUP_MODE: s3
      VEIN_SERVER_BACKUP_S3_BUCKET: backups
      VEIN_SERVER_BACKUP_S3_ENDPOINT: http://garage.localdomain:3900 # Your S3 endpoint url
      VEIN_SERVER_BACKUP_S3_PROVIDER: Other # Optional if your provider is not Other
      VEIN_SERVER_BACKUP_S3_REGION: garage # Optional, some providers care about this
      VEIN_SERVER_BACKUP_S3_KEY_ID: <key id> # required, key id
      VEIN_SERVER_BACKUP_S3_ACCESS_KEY: <secret key> # required secret key
```

## Kubernetes (Helm)

```bash
helm repo add radical-egg https://radical-egg.github.io/pineapple-bun/
helm repo update
helm install vein radical-egg/vein-k8s \
	--set VEIN_SERVER_NAME="Eggs Strange World" \
    --set VEIN_SERVER_DESCRIPTION="nollie 360 flips" \
    --set VEIN_SERVER_PASSWORD="secretpass"
```

The developers have some documentation on what configurations are available [here](https://ramjet.notion.site/Config-279f9ec29f178011a909f8ea9525936d).

## Environment Variables

### Dedicated Server

| Variable | Default | Description |
|---------|---------|-------------|
| PUID    | 1000    | User ID to run the server as |
| PGID    | 1000    | Group ID to run the server as |
| VEIN_SERVER_NAME | "Vein Dedicated Server Docker" | Name of the game server |
| VEIN_SERVER_PASSWORD | "changeme" | Password for game server |
| VEIN_SERVER_DESCRIPTION | "Vein Dedicated server in docker" | Game server description |
| VEIN_SERVER_AUTO_UPDATE | true | Update server on startup |
| VEIN_QUERY_PORT | 27015 | Steam query port (UDP) |
| VEIN_GAME_PORT | 7777 | Game port (UDP) |
| VEIN_SERVER_PUBLIC | true | Specify if the gameserver is public  |
| VEIN_SERVER_HEARTBEAT_INTERVAL | "5.0" | Game server heartbeat interval |
| VEIN_SERVER_MAX_PLAYERS | "16" | Max Players for dedicated server |
| VEIN_SERVER_ADMIN_STEAM_IDS | False | A comma delimited list of AdminSteamIDs |
| VEIN_SERVER_SUPER_ADMIN_STEAM_IDS | False | A comma delimited list of SuperAdminSteamIDs |
| VEIN_SERVER_WHITELISTED_PLAYERS | False | a comma delimited list of WhitelistedPlayers |
| VEIN_SERVER_VAC_ENABLED | 0 | Set bVACEnabled in Game.ini  |
| VEIN_SERVER_USE_BETA | false | Set true to use -beta argument |
| VEIN_SERVER_BETA_BRANCH | experimental | The default branch to use with -beta arugment |
| VEIN_SERVER_VALIDATE_INSTALL | false | Set to true to provide the validate steamcmd argument on server install/update |
| VEIN_SERVER_HTTP_BIND_ADDRESS | 0.0.0.0 | Set the bind address for the HTTP API listener |
| VEIN_SERVER_HTTPPORT | 8080 | Set the HTTPPort value for Game.ini. Requires VEIN_SERVER_ENABLE_HTTP_API is set to true |
| VEIN_SERVER_ENABLE_HTTP_API | False| Set to true to enable HTTP API on VEIN_SERVER_HTTPPORT. By default this is False |  
| VEIN_EXTRA_ARGS | "" | Extra flags passed to the server |

### Dedicated Server Backups

| Variable | Default | Description |
|---------|---------|-------------|
| VEIN_SERVER_BACKUP_MODE | rsync | Possible options are rsync or s3 |
| VEIN_SERVER_BACKUP_S3_BUCKET | "" | Name of s3 bucket |
| VEIN_SERVER_BACKUP_S3_ENDPOINT | "" | s3 endpoint for backups |
| VEIN_SERVER_BACKUP_S3_PROVIDER | Other | name of s3 provider (ex. garage, aws, minio) |
| VEIN_SERVER_BACKUP_S3_REGION | garage | s3 region for rclone configurations, some providers want this |
| VEIN_SERVER_BACKUP_S3_KEY_ID | "" | The access key ID for your s3 bucket |
| VEIN_SERVER_BACKUP_S3_ACCESS_KEY | "" | The s3 access key for your s3 bucket |
| VEIN_SERVER_BACKUP_SRC_DIR | /data | The source directory (in the container) of the dedicated server data |
| VEIN_SERVER_BACKUP_DIR | /backup | The source directory (in the container) of the backup directory |
| VEIN_SERVER_BACKUP_RETENTION | 5 | How many backups to keep (e.x if 10 is specified the 10 most recents will be kept and everything else deleted) |
| VEIN_SERVER_BACKUP_INTERVAL_SECONDS | 3600 | How often to run backups (in seconds) |


## Licensing

This repository and container image include only orchestration code and do NOT distribute any game binaries or assets. Game files are downloaded by the user via SteamCMD under the Steam Subscriber Agreement.

You are responsible for complying with all licenses, terms of service, and EULAs associated with the game.

This project is not affiliated with the game developers or Valve.

## Related resources

Here are some references that may be helpful for configuring VEIN with or without docker.

* VEIN dedicated server setup docs / references (non-Docker): https://vein.wiki.gg/wiki/Vein_Dedicated_Server_Setup
* Developer website for dedicated server setup: https://ramjet.notion.site/dedicated-servers
