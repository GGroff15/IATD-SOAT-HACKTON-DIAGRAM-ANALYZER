from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


DEFAULT_ENV_FILE_PATH = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str
    AWS_ENDPOINT_URL: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_SESSION_TOKEN: Optional[str] = None
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

    # Connection Detection Settings
    CONNECTION_LINE_THRESHOLD: int = 100
    CONNECTION_MIN_LINE_LENGTH: int = 40
    CONNECTION_MAX_LINE_GAP: int = 10
    CONNECTION_CANNY_LOW: int = 50
    CONNECTION_CANNY_HIGH: int = 150
    CONNECTION_PROXIMITY_THRESHOLD: float = 30.0
    CONNECTION_BORDER_MARGIN: float = 4.0
    CONNECTION_MAX_COMPONENT_OVERLAP_RATIO: float = 0.35
    CONNECTION_ANCHOR_DISTANCE_THRESHOLD: Optional[float] = None
    CONNECTION_DEDUP_ENDPOINT_TOLERANCE: float = 10.0
    CONNECTION_DEDUP_ANGLE_TOLERANCE: float = 6.0
    CONNECTION_MORPHOLOGY_KERNEL_SIZE: int = 1
    CONNECTION_MIN_CONFIDENCE: float = 0.45
    CONNECTION_ARROW_WINDOW_SIZE: int = 14
    CONNECTION_MAX_CONNECTIONS_PER_COMPONENT_PAIR: int = 1

    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_QUEUE_NAME: str = "analisys_response"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
