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
      - PUID=1000 # replace with your users UID
      - PGID=1000 # replace with your users GID
      - VEIN_SERVER_AUTO_UPDATE=true
```

After the server has started up you can find the Game.ini in `./data/Vein/Saved/Config/LinuxServer/Game.ini`, configure your settings and restart. The developers have some documentation on
what configurations are available [here](https://ramjet.notion.site/Config-279f9ec29f178011a909f8ea9525936d).


Example:

```
[/Script/Vein.VeinGameSession]
bPublic=True
ServerName=Cool Vein Server
Password=secret
```

## Environment Variables

| Variable | Default | Description |
|---------|---------|-------------|
| PUID    | 1000    | User ID to run the server as |
| PGID    | 1000    | Group ID to run the server as |
| VEIN_SERVER_AUTO_UPDATE | true | Update server on startup |
| VEIN_QUERY_PORT | 27015 | Steam query port (UDP) |
| VEIN_GAME_PORT | 7777 | Game port (UDP) |
| VEIN_EXTRA_ARGS | "" | Extra flags passed to the server |

## Stuff todo

* Add HEALTHCHECK
* Setup trap/graceful stop on SIGINT
* k3s deployment with helm
* Setup github actions to auto publish new images on code change
* Template Game.ini before first install so that environment variables can be passed
for common variables like ServerName etc


## Licensing

This repository and container image include only orchestration code and do NOT distribute any game binaries or assets. Game files are downloaded by the user via SteamCMD under the Steam Subscriber Agreement.

You are responsible for complying with all licenses, terms of service, and EULAs associated with the game.

This project is not affiliated with the game developers or Valve.
