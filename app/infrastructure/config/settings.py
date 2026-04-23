from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


DEFAULT_ENV_FILE_PATH = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # YOLO Inference API Settings
    YOLO_INFERENCE_BASE_URL: str = "http://127.0.0.1:8000"
    YOLO_INFERENCE_INFER_PATH: str = "/infer"
    YOLO_INFERENCE_TIMEOUT_SECONDS: float = 10.0
    YOLO_CONNECTION_ARROW_LINE_CLASS: str = "arrow_line"
    YOLO_CONNECTION_ARROW_HEAD_CLASS: str = "arrow_head"

    # OpenAI-compatible LLM inference settings
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com"
    OPENAI_CHAT_COMPLETIONS_PATH: str = "/v1/chat/completions"
    OPENAI_MODEL: str = "mistral-7b-instruct"
    OPENAI_TIMEOUT_SECONDS: float = 20.0
    OPENAI_TEMPERATURE: float = 0.1
    OPENAI_MAX_TOKENS: int = 900

    # PaddleOCR Settings
    PADDLE_OCR_LANG: str = "en"
    PADDLE_OCR_DEVICE: str = "cpu"
    PADDLE_OCR_USE_ANGLE_CLS: bool = True
    PADDLE_OCR_MODEL_DIR: Optional[str] = None
    PADDLE_OCR_ENABLE_MKLDNN: bool = False

    # File download settings
    FILE_DOWNLOAD_TIMEOUT_SECONDS: float = 30.0

    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_QUEUE_NAME: str = "analisys_response"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
