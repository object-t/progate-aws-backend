from fastapi import APIRouter, Depends
import models.play as play_models
import boto3
from boto3.dynamodb.conditions import Key, Attr
import uuid
from datetime import datetime
from settings import get_DynamoDbConnect
from routers.extractor import extract_user_id_from_token
from routers.costs import get_costs, calculate_final_cost

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
    formatted_data = response.get("Items", [{}])[0]

    return play_models.Scenarioes(**formatted_data)

@play_router.post("/play/create")
# async def create_game(request: play_models.CreateGameRequest, user_id: str = Depends(extract_user_id_from_token)) -> play_models.CreateGameResponse:
async def create_game(request: play_models.CreateGameRequest, user_id: str) -> play_models.CreateGameResponse:
    scenarioes = request.scenarioes
    game_id = str(uuid.uuid4())
    sandbox_id = str(uuid.uuid4())

    game_item = {
        "PK": f"user#{user_id}",
        "SK": f"game#{game_id}",
        "struct": {
            "vpc_resources": [
                {
                    "vpcId": "76827c2d-4a08-41e0-b727-d72f1575b1f8",
                    "vpc": {
                        "id": "76827c2d-4a08-41e0-b727-d72f1575b1f8",
                        "name": "vpc_c8b7e39f70",
                        "type": "vpc"
                    },
                    "availabilityZones": [
                        {
                            "id": "f1de9850-ca68-4c2e-8f89-b8f06d80b311",
                            "name": "Availability Zone A",
                            "type": "az",
                            "vpcId": "76827c2d-4a08-41e0-b727-d72f1575b1f8",
                            "azName": "a"
                        }
                    ],
                    "subnets": [
                        {
                            "id": "35fc1052-3ade-4314-813f-45d0945035d2",
                            "name": "default_subnet_e3d6afee9e",
                            "vpcId": "76827c2d-4a08-41e0-b727-d72f1575b1f8",
                            "azId": "f1de9850-ca68-4c2e-8f89-b8f06d80b311",
                            "isDefault": True,
                            "type": "private_subnet"
                        }
                    ],
                    "networks": [],
                    "computes": [],
                    "databases": []
                }
            ],
            "regional_resources": []
        },
        "funds": 0,
        "current_month": 0,
        "scenarioes": scenarioes,
        "is_finished": False,
        "created_at": datetime.now().isoformat(),
    }

    table.put_item(Item=game_item)

    sandbox_item = {
        "PK": f"user#{user_id}",
        "SK": f"sandbox#{sandbox_id}",
        "struct": None,
        "is_published": False,
        "created_at": datetime.now().isoformat(),
    }

    table.put_item(Item=sandbox_item)

    formatted_response = {
        "user_id": user_id,
        "game_id": game_id,
        "struct": game_item["struct"],
        "funds": game_item["funds"],
        "current_month": game_item["current_month"],
        "scenarioes": game_item["scenarioes"],
        "is_finished": game_item["is_finished"],
        "created_at": game_item["created_at"],
    }

    return play_models.CreateGameResponse(**formatted_response)

@play_router.get("/play/games")
async def get_game(user_id: str = Depends(extract_user_id_from_token)) -> play_models.GetGameResponse:
    formatted_user_id = f"user#{user_id}"

    response = table.query(
        KeyConditionExpression=Key("PK").eq(formatted_user_id) & Key("SK").begins_with("game"),
        FilterExpression=Attr("is_finished").eq(False)
    )
    game_data = response.get("Items", [{}])[0]
    
    formatted_response = {
        "user_id": game_data.get("PK", "").replace("user#", ""),
        "game_id": game_data.get("SK", "").replace("game#", ""),
        "struct": game_data.get("struct"),
        "funds": game_data.get("funds"),
        "current_month": game_data.get("current_month"),
        "scenarioes": game_data.get("scenarioes"),
        "is_finished": game_data.get("is_finished"),
        "created_at": game_data.get("created_at")
    }

    return play_models.GetGameResponse(**formatted_response)

@play_router.post("/play/report/{game_id}")
# async def report_game(game_id: str, user_id: str = Depends(extract_user_id_from_token)):
async def report_game(game_id: str, user_id: str):
    formatted_user_id = f"user#{user_id}"
    formatted_game_id = f"game#{game_id}"
    response = table.query(
        KeyConditionExpression=Key("PK").eq(formatted_user_id) & Key("SK").begins_with(formatted_game_id)
    )
    game_data = response.get("Items", [{}])[0]
    struct_data = game_data.get("struct", {})

    costs_db = await get_costs()

    _requests = 500000 #リクエスト数を仮定

    final_cost = calculate_final_cost(struct_data, costs_db, _requests)

    return {"message": "Report processed", "calculated_cost": final_cost}