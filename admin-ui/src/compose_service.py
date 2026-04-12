from __future__ import annotations

from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap


class ComposeServiceError(RuntimeError):
    pass


class ComposeService:
    def __init__(self, compose_path: Path, service_name: str = "vein") -> None:
        self._compose_path = compose_path
        self._service_name = service_name
        self._yaml = YAML()
        self._yaml.preserve_quotes = True
        self._yaml.width = 4096

    def available(self) -> bool:
        return self._compose_path.exists()

    def config_sync_state(self) -> dict[str, object]:
        if not self.available():
            return {"available": False, "enabled": None, "path": str(self._compose_path)}

        service = self._service()
        raw = self._get_env_value(service, "VEIN_SERVER_SYNC_CONFIG_ON_STARTUP", "true")
        return {
            "available": True,
            "enabled": self._parse_bool(raw),
            "path": str(self._compose_path),
        }

    def set_config_sync(self, enabled: bool) -> dict[str, object]:
        data = self._load()
        service = self._get_service(data)
        self._set_env_value(service, "VEIN_SERVER_SYNC_CONFIG_ON_STARTUP", "true" if enabled else "false")
        self._save(data)
        return self.config_sync_state()

    def apply_env_updates(self, updates: dict[str, str]) -> dict[str, object]:
        if not updates:
            return {"updated": []}

        data = self._load()
        service = self._get_service(data)
        updated = []
        for key, value in updates.items():
            self._set_env_value(service, key, value)
            updated.append({"env_var": key, "value": value})
        self._save(data)
        return {"updated": updated, "path": str(self._compose_path)}

    def read_raw(self) -> str:
        if not self.available():
            raise ComposeServiceError(f"Compose file was not found at {self._compose_path}")
        return self._compose_path.read_text(encoding="utf-8")

    def restore_raw(self, content: str) -> None:
        self._compose_path.write_text(content, encoding="utf-8")

    def _service(self):
        data = self._load()
        return self._get_service(data)

    def _load(self) -> dict:
        if not self.available():
            raise ComposeServiceError(f"Compose file was not found at {self._compose_path}")

        with self._compose_path.open("r", encoding="utf-8") as handle:
            data = self._yaml.load(handle) or CommentedMap()

        return data

    def _save(self, data: dict) -> None:
        with self._compose_path.open("w", encoding="utf-8") as handle:
            self._yaml.dump(data, handle)

    def _get_service(self, data: dict):
        if "services" not in data or self._service_name not in data["services"]:
            raise ComposeServiceError(f"Service {self._service_name} was not found in {self._compose_path}")
        return data["services"][self._service_name]

    @staticmethod
    def _get_env_value(service, key: str, default: object | None = None) -> object | None:
        environment = service.get("environment")

        if environment is None:
            return default

        if isinstance(environment, dict):
            return environment.get(key, default)

        if isinstance(environment, list):
            for item in environment:
                if "=" not in item:
                    continue
                current_key, current_value = item.split("=", 1)
                if current_key == key:
                    return current_value
            return default

        raise ComposeServiceError("Compose environment block must be a map or list")

    @staticmethod
    def _set_env_value(service, key: str, value: str) -> None:
        environment = service.get("environment")

        if environment is None:
            environment = CommentedMap()
            service["environment"] = environment

        if isinstance(environment, dict):
            environment[key] = value
            return

        if isinstance(environment, list):
            for index, item in enumerate(environment):
                if "=" not in item:
                    continue
                current_key, _ = item.split("=", 1)
                if current_key == key:
                    environment[index] = f"{key}={value}"
                    return
            environment.append(f"{key}={value}")
            return

        raise ComposeServiceError("Compose environment block must be a map or list")

    @staticmethod
    def _parse_bool(raw: object) -> bool:
        return str(raw).strip().lower() in {"1", "true", "yes", "on"}
