# Vein Dedicated Server

This is a docker build for the survival game Vein to run a dedicated server. There are some very helpful install instructions [here](https://ramjet.notion.site/Initial-Setup-279f9ec29f17809c9ebce81e96ec48e7) if you are not using docker / this repo.


## Running with docker-compose

```yaml
services:
  vein:
    image: ghcr.io/radical-egg/vein-dedicated-server:latest
    container_name: vein-dedicated-server
    restart: unless-stopped
    ports:
      - "27015:27015/udp"
      - "7777:7777/udp"
    volumes:
      - ./data:/home/vein/server
    environment:
      PUID: 1000 # replace with your users UID
      PGID: 1000 # replace with your users GID
      VEIN_SERVER_AUTO_UPDATE: true
      VEIN_SERVER_NAME: "Vein2Docker"
      VEIN_SERVER_PASSWORD: "secret"
#      VEIN_SERVER_ADMIN_STEAM_IDS: "12345,12345,12345562312"
#      VEIN_SERVER_SUPER_ADMIN_STEAM_IDS: "12345"
  vein-backup-sidecar:
    image: ghcr.io/radical-egg/vein-dedicated-backup:latest
    container_name: vein-dedicated-backup
    volumes:
      - ./data:/data:ro
      - ./backup:/backup:rw
    environment:
      PUID: 1000 # replace with your users UID
      PGID: 1000 # replace with your users GID
      VEIN_SERVER_BACKUP_INTERVAL_SECONDS: 7200
      VEIN_SERVER_BACKUP_RETENTION: 10 # set to 0 to keep all backups
```

The developers have some documentation on what configurations are available [here](https://ramjet.notion.site/Config-279f9ec29f178011a909f8ea9525936d).


## Environment Variables

## Dedicated Server

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
| VEIN_SERVER_NAME | "Vein Dedicated Server Docker" | Name of the game server |
| VEIN_SERVER_HEARTBEAT_INTERVAL | "5.0" | Game server heartbeat interval |
| VEIN_SERVER_MAX_PLAYERS | "16" | Max Players for dedicated server |
| VEIN_SERVER_ADMIN_STEAM_IDS | False | A comma delimited list of AdminSteamIDs |
| VEIN_SERVER_SUPER_ADMIN_STEAM_IDS | False | A comma delimited list of SuperAdminSteamIDs |
| VEIN_SERVER_WHITELISTED_PLAYERS | False | a comma delimited list of WhitelistedPlayers |
| VEIN_SERVER_VAC_ENABLED | 0 | Set bVACEnabled in Game.ini  |
| VEIN_EXTRA_ARGS | "" | Extra flags passed to the server |

## Dedicated Server Backups

| Variable | Default | Description |
|---------|---------|-------------|
| VEIN_SERVER_BACKUP_SRC_DIR | /data | The source directory (in the container) of the dedicated server data |
| VEIN_SERVER_BACKUP_DIR | /backup | The source directory (in the container) of the backup directory |
| VEIN_SERVER_BACKUP_RETENTION | 5 | How many backups to keep (e.x if 10 is specified the 10 most recents will be kept and everything else deleted) |
| VEIN_SERVER_BACKUP_INTERVAL_SECONDS | 3600 | How often to run backups (in seconds)

## Stuff todo

* k3s deployment with helm
* Setup github actions to auto publish new images on code change

## Licensing

This repository and container image include only orchestration code and do NOT distribute any game binaries or assets. Game files are downloaded by the user via SteamCMD under the Steam Subscriber Agreement.

You are responsible for complying with all licenses, terms of service, and EULAs associated with the game.

This project is not affiliated with the game developers or Valve.
