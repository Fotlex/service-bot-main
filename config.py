from pydantic_settings import BaseSettings


class Config(BaseSettings):
    COMPOSE_PROJECT_NAME: str

    BOT_TOKEN: str

    DEBUG: bool
    TIMEZONE: str

    DJANGO_ALLOWED_HOSTS: list[str]

    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: str

    REDIS_HOST: str
    REDIS_PORT: str
    
    BITRIX24_WEBHOOK_URL: str

    class Config:
        env_file = ".env"


config = Config()
