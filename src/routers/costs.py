from fastapi import APIRouter, HTTPException, Depends
import boto3
from boto3.dynamodb.conditions import Key, Attr
import uuid
from routers.extractor import extract_user_id_from_token

from settings import get_DynamoDbConnect

costs_router = APIRouter()

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

table_name = "game"
table = dynamodb.Table(table_name)

@costs_router.get("/costs")
async def get_costs():
    response = table.query(
        KeyConditionExpression=Key("PK").eq("costs") & Key("SK").begins_with("metadata")
    )
    formatted_data = response.get("Items", [{}])[0].get("costs", {})

    return formatted_data