#!/usr/bin/env python3

import re
import os
import configparser
from os import environ

config = configparser.ConfigParser(strict=False)
game_ini_path = environ.get("VEIN_GAME_INI", 
                                "/home/vein/server/Vein/Saved/Config/LinuxServer/Game.ini")

game_ini_map = {
    "/Script/Vein.VeinGameSession": {
        "bPublic": environ.get("VEIN_SERVER_PUBLIC", "true"),
        "ServerName": environ.get("VEIN_SERVER_NAME", "Vein Dedicated Server Docker"),
        "Password": environ.get("VEIN_SERVER_PASSWORD", "changeme"),
        "ServerDescription": environ.get("VEIN_SERVER_DESCRIPTION", "Vein Dedicated server in docker"),
        "HeartbeatInterval": environ.get("VEIN_SERVER_HEARTBEAT_INTERVAL", 5.0),
        "HTTPPort": environ.get("VEIN_SERVER_HTTPPORT", None)
    },
    "/Script/Engine.GameSession": {
        "MaxPlayers": environ.get("VEIN_SERVER_MAX_PLAYERS", 16)
    },
    "OnlineSubsystemSteam": {
        "bVACEnabled": environ.get("VEIN_SERVER_VAC_ENABLED", 0)
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

def multiorder_injection(config_path, section, injector_key, injection):
    start_marker = f"##Start:{injector_key}:injections##\n"
    end_marker   = f"##End:{injector_key}:injections##\n"

    if not os.path.isfile(config_path):
        print(f"path {config_path} does not exists, doing nothing...")
        return

    if isinstance(injection, str):
        injection = injection.splitlines(keepends=True)
    
    injection = [line.strip('"') for line in injection]
    injection = [f"{injector_key}={line}\n" for line in injection]
    injection = [line if line.endswith("\n") else line + "\n" for line in injection]

    injection = [
        injection[0],
        *[f"+{line}" for line in injection[1:]],
    ]

    managed_keys = set()
    for line in injection:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            managed_keys.add(key)

    with open(config_path, "r") as f:
        lines = f.readlines()

    section_header_pattern = re.compile(rf"^\[{re.escape(section)}\]\s*$")
    any_section_pattern    = re.compile(r"^\[.+\]\s*$")

    section_start = None
    for i, line in enumerate(lines):
        if section_header_pattern.match(line.strip()):
            section_start = i
            break

    if section_start is None:
        raise InjectionError(f"Section: {section} is missing..", { "add_section": section})

    section_end = len(lines)
    for i in range(section_start + 1, len(lines)):
        if any_section_pattern.match(lines[i].strip()):
            section_end = i
            break

    start_idx = None
    end_idx = None

    for i in range(section_start + 1, section_end):
        if lines[i].strip() == start_marker.strip():
            start_idx = i
        elif lines[i].strip() == end_marker.strip():
            end_idx = i

    if start_idx is None or end_idx is None:
        body = lines[section_start + 1 : section_end]

        filtered_body = []
        for line in body:
            stripped = line.strip()
            if "=" in stripped and not stripped.startswith("#"):
                key = stripped.split("=", 1)[0].strip()
                if (key.lower() == injector_key.lower() 
                        or key.lower() == f"+{injector_key.lower()}"):
                    continue

            filtered_body.append(line)

        new_lines = (
            lines[: section_start + 1]
            + [start_marker]
            + injection
            + [end_marker]
            + filtered_body
            + lines[section_end:]
        )

    else:
        new_lines = (
            lines[: start_idx + 1]
            + injection
            + lines[end_idx:]
        )

    with open(config_path, "w") as f:
        f.writelines(new_lines)

def sanitize_config_map(config_map) -> dict:
    for section, options in list(config_map.items()):
        for option, value in list(options.items()):
            if value is None:
                del config_map[section][option]
    return config_map

def write_config(config_path, config_map):
    if os.path.isfile(config_path):
        config.read(config_path)

        for key, val in config_map.items():
            if not config.has_section(key):
                config.add_section(key)
            
            for option, config_value in val.items():
                config.set(key, option, str(config_value))

            with open(config_path, "w") as configfile:
                config.write(configfile)

    else:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w") as configfile:
            for key, val in config_map.items():
                config[key] = val
            
            config.write(configfile)

def run_injections(config_path, injection_map, max_attempts=10):
    config.read(config_path)

    for _ in range(1, max_attempts + 1):
        try:
            for section, obj in injection_map.items():
                for key, val in obj.items():
                    if val:
                        items = val.split(",")
                        multiorder_injection(game_ini_path, section, key, items)
                    elif config.has_option(section, key):
                        raise InjectionError(f"{key} is not truthy and needs to be removed", 
                            { "remove_key": { "section": section, "key": key }})
            return
        except InjectionError as e:
            print(f"Attempting to fix {e.data}")

            if "add_section" in e.data:
                config.add_section(e.data["add_section"])
            if "remove_key" in e.data:
                section = e.data["remove_key"]["section"]
                key = e.data["remove_key"]["key"]

                config.remove_option(section, key)
                config.remove_option(section, f"+{key}")

            with open(config_path, "w+") as configfile:
                config.write(configfile)

    raise Exception(f"Reached {max_attempts} attempting to inject game configs")

if __name__ == "__main__":
    try:
        game_ini_map = sanitize_config_map(game_ini_map)

        write_config(game_ini_path, game_ini_map)
        run_injections(game_ini_path, game_ini_multiorder_injections)
    except Exception as e:
        print(e)
        exit(1)
