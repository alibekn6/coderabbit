from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Config(BaseSettings):
    APP_NAME: str = "NotionStats"
    DEBUG: bool = False
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DB_HOST: str
    DB_PORT: int = 5432

    # JWT Configuration
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    NOTION_API_KEY: str
    NOTION_DATABASE_ID: str
    NOTION_PROJECTS_DATABASE_ID: str
    NOTION_KANBAN_DATABASE_ID: str
    NOTION_CONVERSATION_DATABASE_ID: str
    NOTION_VERSION: str = "2022-06-28"

    # Redis & Celery Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None

    # Cache settings
    CACHE_UPDATE_INTERVAL_MINUTES: int = 30

    @property
    def redis_url(self):
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def celery_broker(self):
        return self.CELERY_BROKER_URL or self.redis_url

    @property
    def celery_backend(self):
        return self.CELERY_RESULT_BACKEND or self.redis_url

    @property
    def db_url(self):
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Config()
