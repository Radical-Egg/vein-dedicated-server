from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "admin-ui"))

from src.compose_service import ComposeService


def test_apply_env_updates_preserves_comments_and_updates_map(tmp_path):
    compose_path = tmp_path / "docker-compose.yml"
    compose_path.write_text(
        "services:\n"
        "  vein:\n"
        "    environment:\n"
        "      VEIN_GAME_PORT: 7777 # game port\n",
        encoding="utf-8",
    )

    service = ComposeService(compose_path)
    service.apply_env_updates({"VEIN_GAME_PORT": "7788"})

    updated = compose_path.read_text(encoding="utf-8")
    assert "VEIN_GAME_PORT:" in updated
    assert "7788" in updated
    assert "# game port" in updated


def test_apply_env_updates_preserves_list_environment_shape(tmp_path):
    compose_path = tmp_path / "docker-compose.yml"
    compose_path.write_text(
        "services:\n"
        "  vein:\n"
        "    environment:\n"
        "      - VEIN_GAME_PORT=7777\n"
        "      - TZ=UTC\n",
        encoding="utf-8",
    )

    service = ComposeService(compose_path)
    service.apply_env_updates({"VEIN_GAME_PORT": "7788"})

    updated = compose_path.read_text(encoding="utf-8")
    assert "- VEIN_GAME_PORT=7788" in updated
    assert "- TZ=UTC" in updated
