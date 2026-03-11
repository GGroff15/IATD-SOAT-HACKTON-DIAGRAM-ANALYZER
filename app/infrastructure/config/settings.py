from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    AWS_REGION: str = "us-east-1"
    SQS_QUEUE_URL: str
    S3_BUCKET_NAME: str
    AWS_ENDPOINT_URL: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
