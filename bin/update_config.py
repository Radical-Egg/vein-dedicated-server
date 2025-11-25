#!/usr/bin/env python3

import configparser
import os
from os import environ

game_ini_map = {
    "/Script/Vein.VeinGameSession": {
        "bPublic": environ.get("VEIN_SERVER_PUBLIC", "true"),
        "ServerName": environ.get("VEIN_SERVER_NAME", "Vein Dedicated Server Docker"),
        "Password": environ.get("VEIN_SERVER_PASSWORD", "changeme"),
        "ServerDescription": environ.get("VEIN_SERVER_DESCRIPTION", "Vein Dedicated server in docker"),
        "HeartbeatInterval": environ.get("VEIN_SERVER_HEARTBEAT_INTERVAL", 5.0),
    },
    "/Script/Engine.GameSession": {
        "MaxPlayers": environ.get("VEIN_SERVER_MAX_PLAYERS", 16)
    }
}

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

if __name__ == "__main__":
    config = configparser.ConfigParser()
    game_ini_path = os.environ.get("VEIN_GAME_INI", 
                                 "/home/vein/server/Vein/Saved/Config/LinuxServer/Game.ini")

    try:
        write_config(game_ini_path, game_ini_map)
    except Exception as e:
        print(e)
        exit(1)
