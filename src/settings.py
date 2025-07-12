from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class BedrockSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env", env_file_encoding="utf-8", extra="ignore"
    )

    BEDROCK_REGION: str

class DynamoDbConnect(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env", env_file_encoding="utf-8", extra="ignore"
    )

    REGION: str

class LoadRegion(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env", env_file_encoding="utf-8", extra="ignore"
    )

    REGION: str

class CognitoSettings(LoadRegion):
    USERPOOL_ID: str
    APP_CLIENT_ID: str



@lru_cache()
def get_CognitoSettings() -> CognitoSettings:
    return CognitoSettings()
@lru_cache()
def get_DynamoDbSettings() -> DynamoDbConnect:
    return DynamoDbConnect()
@lru_cache()
def get_BedrockSettings() -> BedrockSettings:
    return BedrockSettings()
