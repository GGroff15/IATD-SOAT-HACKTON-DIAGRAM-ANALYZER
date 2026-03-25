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
    YOLO_MODEL_NAME: str = "yolov8n.pt"
    YOLO_CONFIDENCE_THRESHOLD: float = 0.5
    YOLO_DEVICE: str = "cpu"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
