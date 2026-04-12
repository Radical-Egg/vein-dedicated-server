from __future__ import annotations

import configparser
from dataclasses import dataclass


@dataclass(frozen=True)
class ManagedField:
    file_key: str
    section: str
    option: str
    env_var: str
    description: str


MANAGED_FIELDS = [
    ManagedField("game", "/Script/Vein.VeinGameSession", "bPublic", "VEIN_SERVER_PUBLIC", "Server visibility"),
    ManagedField("game", "/Script/Vein.VeinGameSession", "ServerName", "VEIN_SERVER_NAME", "Server name"),
    ManagedField("game", "/Script/Vein.VeinGameSession", "Password", "VEIN_SERVER_PASSWORD", "Server password"),
    ManagedField("game", "/Script/Vein.VeinGameSession", "ServerDescription", "VEIN_SERVER_DESCRIPTION", "Server description"),
    ManagedField("game", "/Script/Vein.VeinGameSession", "HeartbeatInterval", "VEIN_SERVER_HEARTBEAT_INTERVAL", "Heartbeat interval"),
    ManagedField("game", "/Script/Vein.VeinGameSession", "HTTPPort", "VEIN_SERVER_HTTPPORT", "HTTP API port"),
    ManagedField("game", "/Script/Engine.GameSession", "MaxPlayers", "VEIN_SERVER_MAX_PLAYERS", "Maximum players"),
    ManagedField("game", "OnlineSubsystemSteam", "bVACEnabled", "VEIN_SERVER_VAC_ENABLED", "VAC anti-cheat"),
    ManagedField("game", "OnlineSubsystemSteam", "GameServerQueryPort", "VEIN_QUERY_PORT", "Steam query port"),
    ManagedField("game", "URL", "Port", "VEIN_GAME_PORT", "Game port"),
    ManagedField("engine", "URL", "Port", "VEIN_GAME_PORT", "Game port"),
    ManagedField("engine", "HTTPServer.Listeners", "DefaultBindAddress", "VEIN_SERVER_HTTP_BIND_ADDRESS", "HTTP bind address"),
]


class ManagedConfigService:
    def __init__(self, fields: list[ManagedField] | None = None) -> None:
        self._fields = fields or MANAGED_FIELDS

    def list_fields(self, file_key: str) -> list[dict[str, str]]:
        return [self._serialize(field) for field in self._fields if field.file_key == file_key]

    def detect_changes(self, file_key: str, original_content: str, new_content: str) -> list[dict[str, str]]:
        original = self._parse(original_content)
        updated = self._parse(new_content)
        changes = []

        for field in self._fields:
            if field.file_key != file_key:
                continue

            before = self._read_value(original, field.section, field.option)
            after = self._read_value(updated, field.section, field.option)
            if before == after:
                continue

            item = self._serialize(field)
            item["before"] = before
            item["after"] = after
            changes.append(item)

        return changes

    @staticmethod
    def _parse(content: str) -> configparser.ConfigParser:
        parser = configparser.ConfigParser(strict=False)
        if content.strip():
            parser.read_string(content)
        return parser

    @staticmethod
    def _read_value(parser: configparser.ConfigParser, section: str, option: str) -> str:
        if not parser.has_section(section) or not parser.has_option(section, option):
            return ""
        return parser.get(section, option)

    @staticmethod
    def _serialize(field: ManagedField) -> dict[str, str]:
        return {
            "file_key": field.file_key,
            "section": field.section,
            "option": field.option,
            "env_var": field.env_var,
            "description": field.description,
        }
