#!/usr/bin/env python3

import os
import configparser
from os import environ

from unreal_ini import MissingSectionError
from unreal_ini import UnrealIniDocument

game_config = configparser.ConfigParser(strict=False)
engine_config = configparser.ConfigParser(strict=False)

game_ini_path = environ.get("VEIN_GAME_INI", 
                                "/home/vein/server/Vein/Saved/Config/LinuxServer/Game.ini")

engine_ini_path = environ.get("VEIN_ENGINE_INI",
                                "/home/vein/server/Vein/Saved/Config/LinuxServer/Engine.ini")

engine_ini_map = {
    "URL": {
        "Port": environ.get("VEIN_GAME_PORT", 7777)
    },
    "HTTPServer.Listeners": {
        "DefaultBindAddress": environ.get("VEIN_SERVER_HTTP_BIND_ADDRESS", "0.0.0.0")
    }
}

game_ini_map = {
    "/Script/Vein.VeinGameSession": {
        "bPublic": environ.get("VEIN_SERVER_PUBLIC", "true"),
        "ServerName": environ.get("VEIN_SERVER_NAME", "Vein Dedicated Server Docker"),
        "Password": environ.get("VEIN_SERVER_PASSWORD", "changeme"),
        "ServerDescription": environ.get("VEIN_SERVER_DESCRIPTION", "Vein Dedicated server in docker"),
        "HeartbeatInterval": environ.get("VEIN_SERVER_HEARTBEAT_INTERVAL", 5.0),
        "HTTPPort": environ.get("VEIN_SERVER_HTTPPORT", 8080)
    },
    "/Script/Engine.GameSession": {
        "MaxPlayers": environ.get("VEIN_SERVER_MAX_PLAYERS", 16)
    },
    "OnlineSubsystemSteam": {
        "bVACEnabled": environ.get("VEIN_SERVER_VAC_ENABLED", 0),
        "GameServerQueryPort": environ.get("VEIN_QUERY_PORT", 27015)
    },
    "URL": {
        "Port": environ.get("VEIN_GAME_PORT", 7777)
    }
}

game_ini_multiorder_injections = {
    "/Script/Vein.VeinGameSession": {
        "AdminSteamIDs": environ.get("VEIN_SERVER_ADMIN_STEAM_IDS", False),
        "SuperAdminSteamIDs": environ.get("VEIN_SERVER_SUPER_ADMIN_STEAM_IDS", False),
    },
    "/Script/Vein.VeinGameStateBase": {
        "WhitelistedPlayers": environ.get("VEIN_SERVER_WHITELISTED_PLAYERS", False)
    }
}

class InjectionError(Exception):
    def __init__(self, msg, data):
        super().__init__(msg)
        self.data = data

def reload_config(config, config_path):
    config.clear()
    config.read(config_path)

def multiorder_injection(config_path, section, injector_key, injection):
    if not os.path.isfile(config_path):
        print(f"path {config_path} does not exists, doing nothing...")
        return

    document = UnrealIniDocument.load(config_path)
    try:
        document.set_repeated_option_block(section, injector_key, injection)
    except MissingSectionError:
        raise InjectionError(f"Section: {section} is missing..", { "add_section": section})

    document.save()

def write_config(config, config_path, config_map):
    document = UnrealIniDocument.load(config_path)

    for key, val in config_map.items():
        config_values = {
            option: str(config_value)
            for option, config_value in val.items()
        }
        document.set_options(key, config_values)

    document.save()
    reload_config(config, config_path)

def run_injections(config, config_path, injection_map, max_attempts=10):
    # max_attempts is kept for backwards-compatible callers; the line editor
    # can create/remove the needed sections directly without a repair loop.
    document = UnrealIniDocument.load(config_path)
    original_lines = list(document.lines)

    for section, obj in injection_map.items():
        for key, val in obj.items():
            if val:
                items = val.split(",")
                document.set_repeated_option_block(
                    section,
                    key,
                    items,
                    create_section=True,
                )
            else:
                document.remove_repeated_option(section, key)

    if document.lines != original_lines:
        document.save()

    reload_config(config, config_path)

def env_bool(name: str, default: bool = False):
    raw = environ.get(name)

    if raw is None:
        return default
    
    val = raw.strip().strip('"').strip("'").lower()

    if val in {"true", "yes", "y", "on"}:
        return True
    else:
        return False

if __name__ == "__main__":
    if not env_bool("VEIN_SERVER_ENABLE_HTTP_API", default=False):
        print("VEIN_SERVER_ENABLE_HTTP_API is False.. disabling HTTP API")
        game_ini_map["/Script/Vein.VeinGameSession"]["HTTPPort"] = False

    try:
        write_config(game_config,
                      game_ini_path, game_ini_map)
        run_injections(game_config,
                       game_ini_path, game_ini_multiorder_injections)

        write_config(engine_config,
                    engine_ini_path, engine_ini_map)
    except Exception as e:
        print(e)
        exit(1)
