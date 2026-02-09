# VEIN Dedicated Server Docker Image
[![Release](https://img.shields.io/github/v/release/Radical-Egg/vein-dedicated-server?display_name=tag&sort=semver)](https://github.com/Radical-Egg/vein-dedicated-server/releases)
[![License](https://img.shields.io/github/license/Radical-Egg/vein-dedicated-server)](./LICENSE)
[![Stars](https://img.shields.io/github/stars/Radical-Egg/vein-dedicated-server?style=flat)](https://github.com/Radical-Egg/vein-dedicated-server/stargazers)
[![Issues](https://img.shields.io/github/issues/Radical-Egg/vein-dedicated-server)](https://github.com/Radical-Egg/vein-dedicated-server/issues)
[![Release](https://github.com/Radical-Egg/vein-dedicated-server/actions/workflows/publish-ghcr.yml/badge.svg)](https://github.com/Radical-Egg/vein-dedicated-server/actions/workflows/publish-ghcr.yml)


Run a **VEIN dedicated server** with **Docker Compose** — with optional **automatic updates**, **HTTP API**, and **scheduled backups** (local rsync or S3 via rclone).

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
- [FAQ & Troubleshooting](#faq--troubleshooting)
- [Related Resources](#related-resources)
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

## FAQ & Troubleshooting

This is a list of a frequently asked questions and troubleshooting. **This list usually will be applicable for docker and non-docker users**, so if you are running your server on a Linux or Windows server with steamcmd these solutions generally apply. If they don't, I will be sure to annotate that in the anwsers below.

### Error! App '2131400' state is 0x6 after update job

You may see logs like:

```bash
Public...OK
Waiting for client config...OK
Waiting for user info...OK
Error! App '2131400' state is 0x6 after update job.
...
```

This usually means **SteamCMD failed to install or update the server files**. The most common causes are:

- **Networking** (container can’t reach Steam over HTTPS)
- **Disk space** (not enough free space for download + extraction)
- **Permissions** (SteamCMD can’t write to the install directory)

#### 1) Check networking (inside the container)

SteamCMD needs outbound access to Steam endpoints over **TCP/443**.

Verify HTTPS + DNS from inside the server container:

```bash
docker exec -it vein-dedicated-server curl -I https://api.steampowered.com
```

If this fails, check your DNS settings, firewall rules, proxy, VPN, or restrictive outbound policies.

#### 2) Check free disk space

Downloads can temporarily require extra space during unpacking.

```bash
df -h
```

If you’re using bind mounts / volumes, check the filesystem where your server install actually lives.

#### 3) Check permissions on the install directory

Ensure the user inside the container can **read/write** the install path:

```bash
ls -lah /path/to/gameserver
touch /path/to/gameserver/.perm_test && rm /path/to/gameserver/.perm_test
```

If you’re running rootless or using `PUID/PGID`, make sure the mounted directories on the host are owned by that UID/GID (or are writable).

#### 4) Force SteamCMD to re-download by removing the app manifest (.acf)

SteamCMD tracks install state using an app manifest file at:

`/path/to/gameserver/steamapps/appmanifest_*.acf`

If the manifest is corrupt or the install state is stuck, you can remove it to force a fresh install on the next update cycle:

```bash
rm -f /path/to/gameserver/steamapps/appmanifest_*.acf
```

On the next start/update, SteamCMD should treat the app as not installed and re-download it.

> Note: Only remove the `appmanifest_*.acf` file(s). Don’t delete your saved data/config unless you intend to reset everything.

#### 5) Last resort: install to a new location, then restore from backup

If you’ve confirmed networking/space/permissions and it still fails, the install directory may be in a bad state. The cleanest fix is:

1. Deploy to a new empty install path/volume
2. Let SteamCMD install fresh
3. Restore saves/config from your backups


### How can I restore from a backup?

The gamestate is saved to a file called Server.vns in the SaveGames directory of your gamefiles. The backup “sidecar” container will do an rsync from your gameserver mount -> the backup mount specified in the compose file. The VEIN_SERVER_BACKUP_RETENTION environment variable specifies how many backups to keep. The process of restoring a backup should be relatively straightforward:

1. Stop your server
    ```bash
    docker compose down
    ```

2. Find your `Server.vns` backup file and place it in your SavedGames directory. **Note the below command will overwrite your current Server.vns file, make sure you back it up if you want to keep it**

    ```bash
    cp /path/to/backup/Server.vns /path/to/Save/SavedGames/Server.vns
    ```

3. Start your server back up

    ```bash
    docker compose up -d
    ```

### Warning: Failed to heartbeat (no connection string)

This warning almost always means the dedicated server **can’t be reached from the public internet**, so it fails to complete the heartbeat/registration flow.

The most common causes are:

- **Missing/incorrect port forwarding** on your router (UDP)
  - **Game port:** `7777/udp` (default)
  - **Steam query port:** `27015/udp` (default)
- **Firewall/security rules** blocking inbound UDP to the host (router firewall, host firewall, VPS security group)
- **NAT issues (CGNAT / double NAT)** where inbound connections can’t reach your network at all

> ### Important Note  
> Make sure you’re forwarding **UDP**, not TCP, and that the forwarding target is the **actual host** running the server.  
> Before you test: ensure the server is running  
> UDP “port checks” can be misleading if the server isn’t running.  
> Start the container and confirm it’s listening, then test.

## Verify reachability from the outside world

The most reliable test is from a **different network** (phone hotspot, friend’s network, a cheap VPS, etc.). Testing from inside your own LAN often won’t prove public reachability.

### Option A: Nmap (best quick signal)

```bash
nmap -sU -p 7777 <your.public.ip>
nmap -sU -p 27015 <your.public.ip>
```

Notes:
- UDP scans often show `open|filtered` even when things are fine (because UDP has no handshake).
- If you see `closed`, something is definitely wrong (port not forwarded, firewall, or server not listening).

### Option B: Netcat (UDP probe)

```bash
echo "hello" | nc -u -w2 <your.public.ip> 7777
echo "hello" | nc -u -w2 <your.public.ip> 27015
```

Notes:
- UDP netcat probes don’t always give a clear success/failure signal.
- If it hangs or times out, treat that as “likely not reachable” and continue debugging.



## If it’s not reachable: quick checklist

1) **Docker is exposing the ports**
    - In your compose file, you should have something like:
      - `27015:27015/udp`
      - `7777:7777/udp`

2) **Router port forward is correct**
    - External port → internal host IP → same port (UDP)
    - The internal host IP should be static/reserved via DHCP

3) **Host firewall allows UDP**
    - Linux `ufw` / `firewalld` rules must allow inbound UDP on both ports

4) **CGNAT / double NAT**
    - If your “WAN IP” on your router doesn’t match what websites show as your public IP, you’re likely behind CGNAT.
    - In that case, public hosting may be impossible without a real public IP, a VPN/tunnel solution, or hosting on a VPS.


### Unable to connect to server - `LogHttp: Warning: Request ... waited in queue ...`
If you see warnings like this **and** your server shows up in the server list but **players can’t join** (connection fails/timeouts), a very common cause is **CGNAT** (Carrier-Grade NAT) from your ISP.

**What this means:**  
Some internet providers don’t give your home network its own true public IP address. Instead, you share one with other customers. When that happens, **normal port forwarding often can’t work**, even if you set it up correctly in your router.

**Why the server list can still work:**  
Your server can usually *register itself* with Steam / matchmaking because it makes the first outbound connection. But when a player tries to connect back in, there may be **no direct route to your server**—so the join fails.

**How to confirm:**  
- Check your router’s “WAN / Internet IP”. If it differs from what sites like “what is my IP” show, you’re *likely* behind CGNAT.
- Another hint: your router WAN IP is in ranges like `100.64.x.x` – `100.127.x.x`.

**Fix options:**  
- Some ISPs will allow you to purchase a dedicated IP address, this would solve your issue.
- Host the server on a **VPS / cloud provider** (DigitalOcean, AWS, etc.) where you get a public IP by default.
- Use a **tunneling / relay solution** (example: Cloudflare Tunnel, Tailscale, ZeroTier). These can work around CGNAT, but setup varies by provider and game.

If you’re unsure, your best bet may be to ask your ISP provider directly if you are behind CGNAT.


## Related resources

Here are some references that may be helpful for configuring VEIN with or without docker.

* VEIN dedicated server setup docs / references (non-Docker): https://vein.wiki.gg/wiki/Vein_Dedicated_Server_Setup
* Developer website for dedicated server setup: https://ramjet.notion.site/dedicated-servers
* VEIN config generator: https://vein-germany.de/config/

## Licensing

This repository and container image include only orchestration code and do NOT distribute any game binaries or assets. Game files are downloaded by the user via SteamCMD under the Steam Subscriber Agreement.

You are responsible for complying with all licenses, terms of service, and EULAs associated with the game.

This project is not affiliated with the game developers or Valve.
