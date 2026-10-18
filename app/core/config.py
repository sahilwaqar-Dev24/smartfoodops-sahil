from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "SmartFoodOps"
    VERSION: str = "1.0.0"
    DATABASE_URL: str = "sqlite:///./smartfoodops.db"
    JWT_SECRET: str = "super_secret_jwt_key_change_in_production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    class Config:
        extra = "ignore"

settings = Settings()