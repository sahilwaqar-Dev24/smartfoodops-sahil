from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "SmartFoodOps"
    VERSION: str = "1.0.0"
    DATABASE_URL: str = "sqlite:///./smartfoodops.db"
    # Secret ka koi default nahi: .env (ya environment variable) se aana zaroori hai
    JWT_SECRET: str = Field(min_length=16)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()