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


def test_settings_default_response_queue_uses_ttl(monkeypatch) -> None:
    monkeypatch.delenv("RABBITMQ_QUEUE_NAME", raising=False)
    monkeypatch.delenv("RABBITMQ_MESSAGE_TTL_MS", raising=False)
    monkeypatch.delenv("RABBITMQ_DLX_EXCHANGE_NAME", raising=False)
    monkeypatch.delenv("RABBITMQ_DLQ_QUEUE_NAME", raising=False)
    monkeypatch.delenv("RABBITMQ_DLQ_ROUTING_KEY", raising=False)

    settings = Settings(_env_file=None)

    assert settings.RABBITMQ_QUEUE_NAME == "analysis_response"
    assert settings.RABBITMQ_MESSAGE_TTL_MS == 5000
    assert settings.RABBITMQ_DLX_EXCHANGE_NAME == "analysis_response_dlx_exchange"
    assert settings.RABBITMQ_DLQ_QUEUE_NAME == "analysis_response_dlq_queue"
    assert settings.RABBITMQ_DLQ_ROUTING_KEY == "analysis_response_dlq_routing_key"
