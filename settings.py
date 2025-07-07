from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class CognitoSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    REGION: str
    USERPOOL_ID: str
    APP_CLIENT_ID: str


@lru_cache()
def get_CognitoSettings() -> CognitoSettings:
    return CognitoSettings()
