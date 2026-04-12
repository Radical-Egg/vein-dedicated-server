from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from .compose_service import ComposeService, ComposeServiceError
from .config_service import ConfigFile, ConfigService
from .docker_service import DockerControlError, DockerService, ManagedContainer
from .managed_config import ManagedConfigService


DEFAULT_GAME_INI = "/srv/vein-data/Vein/Saved/Config/LinuxServer/Game.ini"
DEFAULT_ENGINE_INI = "/srv/vein-data/Vein/Saved/Config/LinuxServer/Engine.ini"
DEFAULT_COMPOSE_FILE = "/srv/project/docker-compose.yml"

def create_app(
    config_service: ConfigService | None = None,
    docker_service: DockerService | None = None,
    managed_config_service: ManagedConfigService | None = None,
    compose_service: ComposeService | None = None,
) -> Flask:
    app = Flask(
        __name__,
        static_folder="../static",
        template_folder="../templates",
    )

    game_ini_path = Path(os.environ.get("VEIN_GAME_INI_PATH", DEFAULT_GAME_INI))
    engine_ini_path = Path(os.environ.get("VEIN_ENGINE_INI_PATH", DEFAULT_ENGINE_INI))
    compose_file_path = Path(os.environ.get("VEIN_COMPOSE_FILE_PATH", DEFAULT_COMPOSE_FILE))

    app.config["CONFIG_SERVICE"] = config_service or ConfigService(
        [
            ConfigFile(key="game", label="Game.ini", path=game_ini_path),
            ConfigFile(key="engine", label="Engine.ini", path=engine_ini_path),
        ]
    )
    app.config["DOCKER_SERVICE"] = docker_service or DockerService(
        [
            ManagedContainer(
                key="server",
                label="VEIN Server",
                name=os.environ.get("VEIN_SERVER_CONTAINER_NAME", "vein-dedicated-server"),
            ),
            ManagedContainer(
                key="backup",
                label="Backup Sidecar",
                name=os.environ.get("VEIN_BACKUP_CONTAINER_NAME", "vein-dedicated-backup"),
            ),
        ]
    )
    app.config["MANAGED_CONFIG_SERVICE"] = managed_config_service or ManagedConfigService()
    app.config["COMPOSE_SERVICE"] = compose_service or ComposeService(
        compose_path=compose_file_path,
        service_name=os.environ.get("VEIN_SERVER_SERVICE_NAME", "vein"),
    )

    register_routes(app)
    return app


def register_routes(app: Flask) -> None:
    @app.get("/")
    def index():
        config_service: ConfigService = app.config["CONFIG_SERVICE"]
        compose_service: ComposeService = app.config["COMPOSE_SERVICE"]
        return render_template(
            "index.html",
            config_files=config_service.list_files(),
            compose_available=compose_service.available(),
        )

    @app.get("/api/health")
    def healthcheck():
        return jsonify({"ok": True})

    @app.get("/api/configs")
    def list_configs():
        config_service: ConfigService = app.config["CONFIG_SERVICE"]
        return jsonify({"items": config_service.list_files()})

    @app.get("/api/configs/<key>")
    def get_config(key: str):
        config_service: ConfigService = app.config["CONFIG_SERVICE"]
        managed_service: ManagedConfigService = app.config["MANAGED_CONFIG_SERVICE"]
        try:
            response = config_service.read(key)
            response["managed_fields"] = managed_service.list_fields(key)
            return jsonify(response)
        except KeyError as exc:
            return jsonify({"error": str(exc)}), 404

    @app.put("/api/configs/<key>")
    def update_config(key: str):
        config_service: ConfigService = app.config["CONFIG_SERVICE"]
        managed_service: ManagedConfigService = app.config["MANAGED_CONFIG_SERVICE"]
        compose_service: ComposeService = app.config["COMPOSE_SERVICE"]
        payload = request.get_json(silent=True) or {}
        content = payload.get("content")
        if not isinstance(content, str):
            return jsonify({"error": "content must be a string"}), 400

        try:
            original = config_service.read(key)
            managed_changes = managed_service.detect_changes(key, original["content"], content)
            compose_backup = None

            if managed_changes:
                compose_backup = compose_service.read_raw()
                env_updates = {
                    change["env_var"]: change["after"]
                    for change in managed_changes
                }

                compose_updates = compose_service.apply_env_updates(env_updates)
            else:
                compose_updates = {"updated": []}

            try:
                response = config_service.write(key, content)
            except Exception:
                if compose_backup is not None:
                    compose_service.restore_raw(compose_backup)
                raise

            response["managed_fields"] = managed_service.list_fields(key)
            response["managed_changes"] = managed_changes
            response["compose_updates"] = compose_updates
            return jsonify(response)
        except KeyError as exc:
            return jsonify({"error": str(exc)}), 404
        except ComposeServiceError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.get("/api/startup-sync")
    def startup_sync_state():
        compose_service: ComposeService = app.config["COMPOSE_SERVICE"]
        try:
            return jsonify(compose_service.config_sync_state())
        except ComposeServiceError as exc:
            return jsonify({"error": str(exc)}), 400

    @app.put("/api/startup-sync")
    def update_startup_sync():
        compose_service: ComposeService = app.config["COMPOSE_SERVICE"]
        payload = request.get_json(silent=True) or {}
        enabled = payload.get("enabled")
        if not isinstance(enabled, bool):
            return jsonify({"error": "enabled must be a boolean"}), 400

        try:
            return jsonify(compose_service.set_config_sync(enabled))
        except ComposeServiceError as exc:
            return jsonify({"error": str(exc)}), 400

    @app.get("/api/containers")
    def list_containers():
        docker_service: DockerService = app.config["DOCKER_SERVICE"]
        try:
            return jsonify({"items": docker_service.list_status()})
        except DockerControlError as exc:
            return jsonify({"error": str(exc)}), 502

    @app.post("/api/containers/<key>/<action>")
    def container_action(key: str, action: str):
        docker_service: DockerService = app.config["DOCKER_SERVICE"]
        try:
            return jsonify(docker_service.action(key, action))
        except DockerControlError as exc:
            return jsonify({"error": str(exc)}), 400
