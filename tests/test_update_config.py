#!/usr/bin/env python3
"""Regression tests for the Vein Unreal config writer.

The production script is intentionally line-preserving, so these tests assert
both parsed config values and raw file text. The raw text checks protect
comments, duplicate sections, repeated keys, and managed injection markers.
"""

import sys
import os
import configparser
import subprocess
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))

from update_config import game_ini_map
from update_config import write_config
from update_config import run_injections
import update_config

UPDATE_CONFIG_SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "update_config.py"


def run_update_config_script(tmp_path, env):
    """Run update_config.py with isolated Game.ini and Engine.ini paths."""
    game_ini = tmp_path / "Game.ini"
    engine_ini = tmp_path / "Engine.ini"
    script_env = {
        **os.environ,
        **env,
        "VEIN_GAME_INI": str(game_ini),
        "VEIN_ENGINE_INI": str(engine_ini),
    }

    result = subprocess.run(
        [sys.executable, str(UPDATE_CONFIG_SCRIPT)],
        env=script_env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout

    return game_ini, engine_ini


def read_ini(path):
    """Read an ini file with duplicate-option support enabled."""
    config = configparser.ConfigParser(strict=False)
    config.read(path)
    return config


def test_write_config():
    """write_config creates a Game.ini containing the default scalar map."""
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


def test_update_config_script_applies_config_environment_variables(tmp_path):
    """The script honors every supported environment override."""
    game_ini, engine_ini = run_update_config_script(
        tmp_path,
        {
            "VEIN_SERVER_NAME": "Env Test Server",
            "VEIN_SERVER_PASSWORD": "env-secret",
            "VEIN_SERVER_DESCRIPTION": "Configured from env",
            "VEIN_SERVER_PUBLIC": "false",
            "VEIN_SERVER_HEARTBEAT_INTERVAL": "12.5",
            "VEIN_SERVER_HTTPPORT": "9090",
            "VEIN_SERVER_ENABLE_HTTP_API": "true",
            "VEIN_SERVER_MAX_PLAYERS": "42",
            "VEIN_SERVER_VAC_ENABLED": "1",
            "VEIN_QUERY_PORT": "27016",
            "VEIN_GAME_PORT": "7788",
            "VEIN_SERVER_HTTP_BIND_ADDRESS": "127.0.0.1",
            "VEIN_SERVER_ADMIN_STEAM_IDS": "111,222",
            "VEIN_SERVER_SUPER_ADMIN_STEAM_IDS": "333",
            "VEIN_SERVER_WHITELISTED_PLAYERS": "444,555",
        },
    )

    game = read_ini(game_ini)
    engine = read_ini(engine_ini)
    game_text = game_ini.read_text()

    game_session = "/Script/Vein.VeinGameSession"
    game_state = "/Script/Vein.VeinGameStateBase"

    assert game.get(game_session, "bpublic") == "false"
    assert game.get(game_session, "servername") == "Env Test Server"
    assert game.get(game_session, "password") == "env-secret"
    assert game.get(game_session, "serverdescription") == "Configured from env"
    assert game.get(game_session, "heartbeatinterval") == "12.5"
    assert game.get(game_session, "httpport") == "9090"
    assert game.get("/Script/Engine.GameSession", "maxplayers") == "42"
    assert game.get("OnlineSubsystemSteam", "bvacenabled") == "1"
    assert game.get("OnlineSubsystemSteam", "gameserverqueryport") == "27016"
    assert game.get("URL", "port") == "7788"

    assert engine.get("URL", "port") == "7788"
    assert engine.get("HTTPServer.Listeners", "defaultbindaddress") == "127.0.0.1"

    assert "##Start:AdminSteamIDs:injections##\n" in game_text
    assert "AdminSteamIDs=111\n" in game_text
    assert "AdminSteamIDs=222\n" in game_text
    assert "##Start:SuperAdminSteamIDs:injections##\n" in game_text
    assert "SuperAdminSteamIDs=333\n" in game_text
    assert f"[{game_state}]\n" in game_text
    assert "WhitelistedPlayers=444\n" in game_text
    assert "WhitelistedPlayers=555\n" in game_text


def test_update_config_script_disables_http_api_by_default(tmp_path):
    """HTTP API config is disabled unless the opt-in flag is true."""
    game_ini, engine_ini = run_update_config_script(
        tmp_path,
        {
            "VEIN_SERVER_HTTPPORT": "9090",
        },
    )

    game = read_ini(game_ini)
    engine = read_ini(engine_ini)

    assert game.get("/Script/Vein.VeinGameSession", "httpport") == "False"
    assert engine.get("HTTPServer.Listeners", "defaultbindaddress") == "0.0.0.0"


def test_write_config_preserves_false_values(tmp_path):
    """False values are written literally instead of being treated as missing."""
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


def test_write_config_updates_existing_lowercase_managed_keys(tmp_path):
    """Existing managed keys are matched case-insensitively."""
    config = configparser.ConfigParser(strict=False)
    game_ini = tmp_path / "Game.ini"
    game_ini.write_text(
        "[URL]\n"
        "port = 27015\n"
    )

    write_config(config, str(game_ini), {"URL": {"Port": 7777}})

    written = game_ini.read_text()

    assert "Port = 7777\n" in written
    assert "port = 27015\n" not in written


def test_write_config_preserves_unmanaged_comments_duplicates_and_sections(tmp_path):
    """Unmanaged comments, duplicate keys, and duplicate sections survive writes."""
    config = configparser.ConfigParser(strict=False)
    game_ini = tmp_path / "Game.ini"
    game_ini.write_text(
        "; user-managed top-level comment\n"
        "[/Script/Vein.VeinGameSession]\n"
        "; user-managed section comment\n"
        "ServerName = Old Name\n"
        "CustomArray = one\n"
        "CustomArray = two\n"
        "\n"
        "[Custom.Section]\n"
        "Foo = first\n"
        "Foo = second\n"
        "\n"
        "[Custom.Section]\n"
        "Foo = third\n"
    )

    write_config(
        config,
        str(game_ini),
        {
            "/Script/Vein.VeinGameSession": {
                "ServerName": "New Name",
            },
        },
    )

    written = game_ini.read_text()

    assert "; user-managed top-level comment\n" in written
    assert "; user-managed section comment\n" in written
    assert "ServerName = New Name\n" in written
    assert "ServerName = Old Name\n" not in written
    assert written.count("CustomArray = one\n") == 1
    assert written.count("CustomArray = two\n") == 1
    assert written.count("[Custom.Section]\n") == 2
    assert written.count("Foo = first\n") == 1
    assert written.count("Foo = second\n") == 1
    assert written.count("Foo = third\n") == 1


def test_write_config_allows_percent_values(tmp_path):
    """Percent characters are written without ConfigParser interpolation errors."""
    config = configparser.ConfigParser(strict=False)
    game_ini = tmp_path / "Game.ini"

    write_config(
        config,
        str(game_ini),
        {
            "/Script/Vein.VeinGameSession": {
                "Password": "100%secret",
            },
        },
    )

    assert "Password = 100%secret\n" in game_ini.read_text()


def test_write_config_creates_file_without_parent_dir(tmp_path, monkeypatch):
    """Relative config paths in the current directory are supported."""
    monkeypatch.chdir(tmp_path)
    config = configparser.ConfigParser(strict=False)

    write_config(
        config,
        "Game.ini",
        {
            "URL": {
                "Port": 7777,
            },
        },
    )

    written = configparser.ConfigParser(strict=False)
    written.read("Game.ini")

    assert written.get("URL", "port") == "7777"


def test_write_config_handles_section_without_final_newline(tmp_path):
    """A header-only file is normalized before appending new options."""
    config = configparser.ConfigParser(strict=False)
    game_ini = tmp_path / "Game.ini"
    game_ini.write_text("[URL]")

    write_config(config, str(game_ini), {"URL": {"Port": 7777}})

    assert game_ini.read_text() == "[URL]\nPort = 7777\n"


def test_run_injections_uses_supplied_config_path(tmp_path, monkeypatch):
    """run_injections writes to its argument instead of global module paths."""
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


def test_run_injections_adds_missing_section_without_rewriting_file(tmp_path):
    """Missing injection sections are appended without rewriting unrelated text."""
    game_ini = tmp_path / "Game.ini"
    game_ini.write_text(
        "; keep me\n"
        "[Custom.Section]\n"
        "Foo = first\n"
        "Foo = second\n"
    )

    config = configparser.ConfigParser(strict=False)
    injection_map = {
        "/Script/Vein.VeinGameStateBase": {
            "WhitelistedPlayers": "abc123",
        },
    }

    run_injections(config, str(game_ini), injection_map)

    written = game_ini.read_text()

    assert "; keep me\n" in written
    assert written.count("Foo = first\n") == 1
    assert written.count("Foo = second\n") == 1
    assert "[/Script/Vein.VeinGameStateBase]\n" in written
    assert "##Start:WhitelistedPlayers:injections##\n" in written
    assert "WhitelistedPlayers=abc123\n" in written
    assert "##End:WhitelistedPlayers:injections##\n" in written


def test_run_injections_handles_section_without_final_newline(tmp_path):
    """Injection blocks are separated correctly from a final unterminated header."""
    game_ini = tmp_path / "Game.ini"
    game_ini.write_text("[/Script/Vein.VeinGameSession]")

    config = configparser.ConfigParser(strict=False)
    injection_map = {
        "/Script/Vein.VeinGameSession": {
            "AdminSteamIDs": "111",
        },
    }

    run_injections(config, str(game_ini), injection_map)

    assert game_ini.read_text() == (
        "[/Script/Vein.VeinGameSession]\n"
        "##Start:AdminSteamIDs:injections##\n"
        "AdminSteamIDs=111\n"
        "##End:AdminSteamIDs:injections##\n"
    )


def test_run_injections_removes_stale_disabled_key(tmp_path):
    """Disabled injection values remove stale unmarked repeated keys."""
    game_ini = tmp_path / "Game.ini"
    game_ini.write_text(
        "[/Script/Vein.VeinGameSession]\n"
        "AdminSteamIDs=111\n"
        "ServerName=Test Server\n"
    )

    config = configparser.ConfigParser(strict=False)
    injection_map = {
        "/Script/Vein.VeinGameSession": {
            "AdminSteamIDs": False,
        },
    }

    run_injections(config, str(game_ini), injection_map)

    written = configparser.ConfigParser(strict=False)
    written.read(game_ini)

    assert not written.has_option("/Script/Vein.VeinGameSession", "AdminSteamIDs")
    assert written.get("/Script/Vein.VeinGameSession", "servername") == "Test Server"


def test_run_injections_removes_stale_disabled_key_without_rewriting_file(tmp_path):
    """Disabled injection blocks are removed while preserving unrelated lines."""
    game_ini = tmp_path / "Game.ini"
    game_ini.write_text(
        "; keep me\n"
        "[/Script/Vein.VeinGameSession]\n"
        "##Start:AdminSteamIDs:injections##\n"
        "AdminSteamIDs=111\n"
        "AdminSteamIDs=222\n"
        "##End:AdminSteamIDs:injections##\n"
        "CustomArray = one\n"
        "CustomArray = two\n"
        "\n"
        "[Custom.Section]\n"
        "Foo = first\n"
        "Foo = second\n"
    )

    config = configparser.ConfigParser(strict=False)
    injection_map = {
        "/Script/Vein.VeinGameSession": {
            "AdminSteamIDs": False,
        },
    }

    run_injections(config, str(game_ini), injection_map)

    written = game_ini.read_text()

    assert "; keep me\n" in written
    assert "##Start:AdminSteamIDs:injections##" not in written
    assert "AdminSteamIDs=111\n" not in written
    assert "AdminSteamIDs=222\n" not in written
    assert "##End:AdminSteamIDs:injections##" not in written
    assert written.count("CustomArray = one\n") == 1
    assert written.count("CustomArray = two\n") == 1
    assert written.count("Foo = first\n") == 1
    assert written.count("Foo = second\n") == 1
