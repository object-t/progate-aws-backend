from fastapi import APIRouter, Depends
import models.play as play_models
import boto3
from boto3.dynamodb.conditions import Key
import uuid
from datetime import datetime
from settings import get_DynamoDbConnect
from routers.extractor import extract_user_id_from_token

play_router = APIRouter()

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

@play_router.get("/play/scenarioes")
async def get_scenarioes(user_id: str = Depends(extract_user_id_from_token)) -> play_models.Scenarioes:
    response = table.query(
        KeyConditionExpression=Key("PK").eq("entity") & Key("SK").eq("metadata")
    )
    data = response.get("Items", [{}])[0].get("scenarioes", {})

    return play_models.Scenarioes(**data)

@play_router.post("/play/create")
async def create_game(request: play_models.CreateGameRequest, user_id: str = Depends(extract_user_id_from_token)) -> play_models.CreateGameResponse:
    scenarioes = request.scenarioes
    game_id = str(uuid.uuid4())

    item = {
        "PK": user_id,
        "SK": game_id,
        "struct": None,
        "funds": 0,
        "current_month": 0, 
        "scenarioes": scenarioes,
        "is_finished": False,
        "created_at": datetime.now().isoformat(),
    }

    table.put_item(Item=item)

    formatted_response = {
        "user_id": user_id,
        "game_id": game_id,
        "struct": item["struct"],
        "funds": item["funds"],
        "current_month": item["current_month"],
        "scenarioes": item["scenarioes"],
        "is_finished": item["is_finished"],
        "created_at": item["created_at"],
    }

    return play_models.CreateGameResponse(**formatted_response)