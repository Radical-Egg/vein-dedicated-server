#!/usr/bin/env python3
import sys
import os
import configparser
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))

from update_config import game_ini_map
from update_config import write_config
from update_config import run_injections
import update_config

def test_write_config():
    config = configparser.ConfigParser(strict=False)
    game_ini = tempfile.mkstemp()[1]
    
    write_config(config, game_ini, game_ini_map)

    assert(os.path.isfile(game_ini))
    assert(config.read(game_ini))

    for c in game_ini_map:
        assert(c in config)
        for key, expected in game_ini_map[c].items():
            key = key.lower()
 
            assert(config[c].get(key))
            assert(str(expected) == str(config[c].get(key)))


def test_write_config_preserves_false_values(tmp_path):
    config = configparser.ConfigParser(strict=False)
    game_ini = tmp_path / "Game.ini"
    game_ini.write_text(
        "[/Script/Vein.VeinGameSession]\n"
        "HTTPPort = 8080\n"
        "ServerName = Existing Name\n"
    )

    config_map = {
        "/Script/Vein.VeinGameSession": {
            "HTTPPort": False,
            "ServerName": "Updated Name",
        }
    }

    write_config(config, str(game_ini), config_map)

    written = configparser.ConfigParser(strict=False)
    written.read(game_ini)

    assert written.get("/Script/Vein.VeinGameSession", "httpport") == "False"
    assert written.get("/Script/Vein.VeinGameSession", "servername") == "Updated Name"


def test_run_injections_uses_supplied_config_path(tmp_path, monkeypatch):
    target_path = tmp_path / "Game.ini"
    other_path = tmp_path / "unexpected.ini"

    base_ini = (
        "[/Script/Vein.VeinGameSession]\n"
        "ServerName = Test Server\n\n"
        "[/Script/Vein.VeinGameStateBase]\n"
    )

    target_path.write_text(base_ini)
    other_path.write_text(base_ini)

    monkeypatch.setattr(update_config, "game_ini_path", str(other_path))

    config = configparser.ConfigParser(strict=False)
    injection_map = {
        "/Script/Vein.VeinGameSession": {
            "AdminSteamIDs": "111,222",
        },
        "/Script/Vein.VeinGameStateBase": {
            "WhitelistedPlayers": "abc123",
        },
    }

    run_injections(config, str(target_path), injection_map)

    target_text = target_path.read_text()
    other_text = other_path.read_text()

    assert "##Start:AdminSteamIDs:injections##" in target_text
    assert "AdminSteamIDs=111\n" in target_text
    assert "AdminSteamIDs=222\n" in target_text
    assert "WhitelistedPlayers=abc123\n" in target_text
    assert "##Start:AdminSteamIDs:injections##" not in other_text
