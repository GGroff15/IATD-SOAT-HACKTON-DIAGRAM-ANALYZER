from pathlib import Path

from app.infrastructure.config.settings import DEFAULT_ENV_FILE_PATH, Settings


def test_settings_model_uses_absolute_env_file_path() -> None:
    env_file = Settings.model_config.get("env_file")

    assert env_file is not None
    assert DEFAULT_ENV_FILE_PATH.is_absolute()
    assert Path(str(env_file)) == DEFAULT_ENV_FILE_PATH


def test_default_env_file_path_points_to_project_root() -> None:
    expected_path = Path(__file__).resolve().parents[4] / ".env"

    assert DEFAULT_ENV_FILE_PATH == expected_path
