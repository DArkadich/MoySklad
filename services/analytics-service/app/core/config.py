import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    LOG_LEVEL: str = "INFO"
    class Config:
        env_file = ".env"

settings = Settings() 