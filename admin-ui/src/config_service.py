from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ConfigFile:
    key: str
    label: str
    path: Path


class ConfigService:
    def __init__(self, config_files: list[ConfigFile]) -> None:
        self._config_files = {config.key: config for config in config_files}

    def list_files(self) -> list[dict[str, str]]:
        return [
            {
                "key": config.key,
                "label": config.label,
                "path": str(config.path),
                "exists": config.path.exists(),
            }
            for config in self._config_files.values()
        ]

    def read(self, key: str) -> dict[str, str]:
        config = self._get(key)
        content = config.path.read_text(encoding="utf-8") if config.path.exists() else ""
        return {
            "key": config.key,
            "label": config.label,
            "path": str(config.path),
            "content": content,
        }

    def write(self, key: str, content: str) -> dict[str, str]:
        config = self._get(key)
        config.path.parent.mkdir(parents=True, exist_ok=True)
        config.path.write_text(content, encoding="utf-8")
        return self.read(key)

    def _get(self, key: str) -> ConfigFile:
        if key not in self._config_files:
            raise KeyError(f"Unknown config key: {key}")
        return self._config_files[key]
