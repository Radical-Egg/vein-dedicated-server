from __future__ import annotations

from dataclasses import dataclass

import docker
from docker.errors import DockerException, NotFound


@dataclass(frozen=True)
class ManagedContainer:
    key: str
    label: str
    name: str


class DockerControlError(RuntimeError):
    pass


class DockerService:
    def __init__(self, containers: list[ManagedContainer], client: docker.DockerClient | None = None) -> None:
        self._containers = {container.key: container for container in containers}
        self._client = client or docker.from_env()

    def list_status(self) -> list[dict[str, str]]:
        return [self.inspect(container.key) for container in self._containers.values()]

    def inspect(self, key: str) -> dict[str, str]:
        managed = self._get(key)
        try:
            container = self._client.containers.get(managed.name)
            container.reload()
            return {
                "key": managed.key,
                "label": managed.label,
                "name": managed.name,
                "status": container.status,
                "health": self._health(container),
                "image": container.image.tags[0] if container.image.tags else container.image.short_id,
            }
        except NotFound:
            return {
                "key": managed.key,
                "label": managed.label,
                "name": managed.name,
                "status": "missing",
                "health": "unknown",
                "image": "",
            }
        except DockerException as exc:
            raise DockerControlError(str(exc)) from exc

    def action(self, key: str, command: str) -> dict[str, str]:
        managed = self._get(key)
        try:
            container = self._client.containers.get(managed.name)
            if command == "start":
                container.start()
            elif command == "stop":
                container.stop(timeout=20)
            elif command == "restart":
                container.restart(timeout=20)
            else:
                raise DockerControlError(f"Unsupported action: {command}")
            container.reload()
            return self.inspect(key)
        except NotFound as exc:
            raise DockerControlError(f"Container {managed.name} was not found") from exc
        except DockerException as exc:
            raise DockerControlError(str(exc)) from exc

    def _get(self, key: str) -> ManagedContainer:
        if key not in self._containers:
            raise DockerControlError(f"Unknown container key: {key}")
        return self._containers[key]

    @staticmethod
    def _health(container) -> str:
        state = getattr(container, "attrs", {}).get("State", {})
        return state.get("Health", {}).get("Status", "none")
