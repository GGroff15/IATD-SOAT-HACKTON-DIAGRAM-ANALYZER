from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str
    AWS_ENDPOINT_URL: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_SESSION_TOKEN: Optional[str] = None
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # YOLO Detection Settings
    YOLO_MODEL_NAME: str = "best.pt"
    YOLO_CONFIDENCE_THRESHOLD: float = 0.5
    YOLO_DEVICE: str = "cpu"
    YOLO_CONNECTION_ARROW_LINE_CLASS: str = "arrow_line"
    YOLO_CONNECTION_ARROW_HEAD_CLASS: str = "arrow_head"

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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
