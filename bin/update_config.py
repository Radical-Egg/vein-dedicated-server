#!/usr/bin/env python3
"""Generate Vein dedicated server Unreal config from environment variables.

The container starts with environment variables as its user-facing interface.
This script translates those values into ``Game.ini`` and ``Engine.ini`` while
preserving any unrelated settings already present in the Unreal-generated
files.
"""

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

# Scalar options are written as ``Option = value`` entries. Values come from
# the environment at import time so tests can exercise the script in a child
# process with a controlled environment.
engine_ini_map = {
    "URL": {
        "Port": environ.get("VEIN_GAME_PORT", 7777)
    },
    "HTTPServer.Listeners": {
        "DefaultBindAddress": environ.get("VEIN_SERVER_HTTP_BIND_ADDRESS", "0.0.0.0")
    }
}

# Game.ini owns the gameplay/session-facing values that players and Steam
# clients observe when connecting to the dedicated server.
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

# Repeated-key options cannot be represented safely by ConfigParser writes, so
# these values are handled separately as managed injection blocks.
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
    """Raised when a repeated-key injection cannot be applied safely."""

    def __init__(self, msg, data):
        """Store a human-readable message and structured recovery data."""
        super().__init__(msg)
        self.data = data


def reload_config(config, config_path):
    """Refresh a ``ConfigParser`` instance from the file on disk."""
    config.clear()
    config.read(config_path)


def multiorder_injection(config_path, section, injector_key, injection):
    """Write one repeated-key injection block into an existing ini section.

    This legacy helper keeps its original missing-file behavior for callers
    that expect it to be a no-op when the config has not been generated yet.
    """
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
    """Write scalar config options and reload ``config`` from disk."""
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
    """Apply or remove repeated-key injection blocks and reload ``config``."""
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
    """Read a permissive true/false environment flag."""
    raw = environ.get(name)

    if raw is None:
        return default

    val = raw.strip().strip('"').strip("'").lower()

    if val in {"true", "yes", "y", "on", "1"}:
        return True
    else:
        return False


if __name__ == "__main__":
    # The HTTP API is opt-in. When disabled, keep the key present but write the
    # value Unreal expects for a disabled port.
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
