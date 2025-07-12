from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class LoadRegion(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    REGION: str

class CognitoSettings(LoadRegion):
    USERPOOL_ID: str
    APP_CLIENT_ID: str

class DynamoDbConnect(LoadRegion):
    DYNAMODB_ENDPOINT: str
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str



@lru_cache()
def get_CognitoSettings() -> CognitoSettings:
    return CognitoSettings()
@lru_cache()
def get_DynamoDbConnect() -> DynamoDbConnect:
    return DynamoDbConnect()
