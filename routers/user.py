from fastapi import APIRouter, HTTPException, Depends
import models.user as user_models
import boto3
from settings import get_DynamoDbConnect
from routers.extractor import extract_user_id_from_token

user_router = APIRouter()

settings = get_DynamoDbConnect()

DYNAMODB_ENDPOINT = settings.DYNAMODB_ENDPOINT
REGION = settings.REGION
AWS_ACCESS_KEY_ID = settings.AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY = settings.AWS_SECRET_ACCESS_KEY

dynamodb = boto3.resource(
    "dynamodb",
    endpoint_url=DYNAMODB_ENDPOINT,
    region_name=REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

table_name = "users"
table = dynamodb.Table(table_name)

@user_router.post("/user")
async def save_user(username: user_models.UserName, UserId: str = Depends(extract_user_id_from_token)):
    User = user_models.User(
        username=username.username,
        UserId=UserId
    )

    try:
        table.put_item(Item=User.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"message": "ユーザー登録完了", "user": username.model_dump()}
