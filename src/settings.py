import os
from functools import lru_cache
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv("../.env")

class BedrockSettings:
    def __init__(self):
        self.BEDROCK_REGION: str = os.getenv("BEDROCK_REGION", "")

class DynamoDbConnect:
    def __init__(self):
        self.REGION: str = os.getenv("REGION", "")

class LoadRegion:
    def __init__(self):
        self.REGION: str = os.getenv("REGION", "")

class CognitoSettings:
    def __init__(self):
        self.REGION: str = os.getenv("REGION", "")
        self.USERPOOL_ID: str = os.getenv("USERPOOL_ID", "")
        self.APP_CLIENT_ID: str = os.getenv("APP_CLIENT_ID", "")



@lru_cache()
def get_CognitoSettings() -> CognitoSettings:
    return CognitoSettings()
@lru_cache()
def get_DynamoDbSettings() -> DynamoDbConnect:
    return DynamoDbConnect()
@lru_cache()
def get_BedrockSettings() -> BedrockSettings:
    return BedrockSettings()
