import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "admin-ui"))

from src.app import create_app
from src.docker_service import DockerControlError


class FakeDockerService:
    def __init__(self) -> None:
        self.actions = []

    def list_status(self):
        return [
            {
                "key": "server",
                "label": "VEIN Server",
                "name": "vein-dedicated-server",
                "status": "running",
                "health": "healthy",
                "image": "vein:test",
            }
        ]

    def action(self, key, action):
        self.actions.append((key, action))
        if key != "server":
            raise DockerControlError("missing")
        return {
            "key": key,
            "label": "VEIN Server",
            "name": "vein-dedicated-server",
            "status": "running",
            "health": "healthy",
            "image": "vein:test",
        }


class FakeComposeService:
    def __init__(self) -> None:
        self.sync_enabled = True
        self.env_updates = []
        self.raw = "services:\n  vein:\n    environment:\n      VEIN_GAME_PORT: 7777\n"
        self.fail_apply = False

    def available(self):
        return True

    def config_sync_state(self):
        return {"available": True, "enabled": self.sync_enabled, "path": "/tmp/docker-compose.yml"}

    def set_config_sync(self, enabled):
        self.sync_enabled = enabled
        return self.config_sync_state()

    def read_raw(self):
        return self.raw

    def restore_raw(self, content):
        self.raw = content

    def apply_env_updates(self, updates):
        if self.fail_apply:
            raise RuntimeError("compose update failed")
        self.env_updates.append(updates)
        return {
            "updated": [{"env_var": key, "value": value} for key, value in updates.items()],
            "path": "/tmp/docker-compose.yml",
        }


@pytest.fixture()
def app(tmp_path, monkeypatch):
    game_ini = tmp_path / "Vein" / "Saved" / "Config" / "LinuxServer" / "Game.ini"
    engine_ini = tmp_path / "Vein" / "Saved" / "Config" / "LinuxServer" / "Engine.ini"
    monkeypatch.setenv("VEIN_GAME_INI_PATH", str(game_ini))
    monkeypatch.setenv("VEIN_ENGINE_INI_PATH", str(engine_ini))

    app = create_app(
        docker_service=FakeDockerService(),
        compose_service=FakeComposeService(),
    )
    app.config["TESTING"] = True
    return app


def test_get_and_put_config(app):
    client = app.test_client()

    response = client.put("/api/configs/game", json={"content": "[Section]\nKey=Value\n"})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["content"] == "[Section]\nKey=Value\n"

    response = client.get("/api/configs/game")
    assert response.status_code == 200
    assert response.get_json()["path"].endswith(str(Path("Game.ini")))
    assert response.get_json()["managed_fields"]


def test_put_config_can_sync_managed_values_into_compose(app):
    client = app.test_client()

    initial = "[URL]\nPort=7777\n"
    updated = "[URL]\nPort=7788\n"

    response = client.put("/api/configs/game", json={"content": initial})
    assert response.status_code == 200

    response = client.put(
        "/api/configs/game",
        json={"content": updated},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["managed_changes"][0]["env_var"] == "VEIN_GAME_PORT"
    assert payload["compose_updates"]["updated"][0]["value"] == "7788"


def test_container_routes(app):
    client = app.test_client()

    response = client.get("/api/containers")
    assert response.status_code == 200
    assert response.get_json()["items"][0]["status"] == "running"

    response = client.post("/api/containers/server/restart")
    assert response.status_code == 200
    assert response.get_json()["name"] == "vein-dedicated-server"


def test_startup_sync_routes(app):
    client = app.test_client()

    response = client.get("/api/startup-sync")
    assert response.status_code == 200
    assert response.get_json()["enabled"] is True

    response = client.put("/api/startup-sync", json={"enabled": False})
    assert response.status_code == 200
    assert response.get_json()["enabled"] is False


def test_put_config_does_not_write_ini_when_compose_sync_fails(app):
    client = app.test_client()

    original = "[URL]\nPort=7777\n"
    client.put("/api/configs/game", json={"content": original})

    compose = app.config["COMPOSE_SERVICE"]
    compose.fail_apply = True

    response = client.put("/api/configs/game", json={"content": "[URL]\nPort=7788\n"})
    assert response.status_code == 500 or response.status_code == 400

    response = client.get("/api/configs/game")
    assert response.get_json()["content"] == original
