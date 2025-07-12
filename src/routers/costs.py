from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import boto3
from boto3.dynamodb.conditions import Key, Attr
import uuid
from decimal import Decimal
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

class CostCalculationRequest(BaseModel):
    struct_data: dict
    num_requests: int = 1000

class GameDataRequest(BaseModel):
    user_id: str = None
    game_id: str = None
    struct: dict
    regional_resources: list = []
    funds: int = 0
    current_month: int = 0
    scenarioes: str = ""
    is_finished: bool = False
    created_at: str = ""

def calculate_final_cost(struct_data: dict, costs_db: dict, num_requests: int) -> float:
    """
    インフラ構成と料金DBから、月額固定費とリクエスト変動費を考慮した最終コストを計算する。
    """
    monthly_cost = 0.0
    per_request_cost = 0.0

    for resource_type in find_resource_types(struct_data):
        if resource_type in costs_db:
            resource_info = costs_db[resource_type]
            cost = float(resource_info.get("cost", 0))
            billing_type = resource_info.get("type")

            if billing_type == "per_month":
                monthly_cost += cost
            elif billing_type == "per_request":
                per_request_cost += cost
    
    final_cost = monthly_cost + (per_request_cost * num_requests)
    return final_cost

@costs_router.get("/costs")
async def get_costs():
    response = table.query(
        KeyConditionExpression=Key("PK").eq("costs") & Key("SK").begins_with("metadata")
    )
    formatted_data = response.get("Items", [{}])[0].get("costs", {})

    return formatted_data

@costs_router.post("/calculate")
async def calculate_cost(request: CostCalculationRequest):
    response = table.query(
        KeyConditionExpression=Key("PK").eq("costs") & Key("SK").begins_with("metadata")
    )
    costs_db = response.get("Items", [{}])[0].get("costs", {})
    
    if not costs_db:
        raise HTTPException(status_code=404, detail="Cost data not found")
    
    final_cost = calculate_final_cost(request.struct_data, costs_db, request.num_requests)
    resource_types = list(find_resource_types(request.struct_data))
    
    monthly_cost = sum(float(costs_db.get(t, {}).get("cost", 0)) for t in resource_types if costs_db.get(t, {}).get("type") == "per_month")
    request_cost = sum(float(costs_db.get(t, {}).get("cost", 0)) for t in resource_types if costs_db.get(t, {}).get("type") == "per_request") * request.num_requests
    
    return {
        "final_cost": final_cost,
        "num_requests": request.num_requests,
        "resource_types": resource_types,
        "breakdown": {
            "monthly_cost": monthly_cost,
            "request_cost": request_cost
        }
    }

@costs_router.post("/calculate-game")
async def calculate_game_cost(game_data: dict):
    try:
        response = table.query(
            KeyConditionExpression=Key("PK").eq("costs") & Key("SK").begins_with("metadata")
        )
        costs_db = response.get("Items", [{}])[0].get("costs", {})
        
        if not costs_db:
            raise HTTPException(status_code=404, detail="Cost data not found")
        
        struct_data = game_data.get("struct", {})
        num_requests = 1000
        
        final_cost = calculate_final_cost(struct_data, costs_db, num_requests)
        resource_types = list(find_resource_types(struct_data))
        
        monthly_cost = sum(float(costs_db.get(t, {}).get("cost", 0)) for t in resource_types if costs_db.get(t, {}).get("type") == "per_month")
        request_cost = sum(float(costs_db.get(t, {}).get("cost", 0)) for t in resource_types if costs_db.get(t, {}).get("type") == "per_request") * num_requests
        
        return {
            "user_id": game_data.get("user_id"),
            "game_id": game_data.get("game_id"),
            "final_cost": final_cost,
            "num_requests": num_requests,
            "resource_types": resource_types,
            "breakdown": {
                "monthly_cost": monthly_cost,
                "request_cost": request_cost
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating cost: {str(e)}")

def find_resource_types(data):
    """structデータからリソースタイプを抽出するヘルパー関数"""
    if isinstance(data, dict):
        if "type" in data:
            yield data["type"]
        for value in data.values():
            yield from find_resource_types(value)
    elif isinstance(data, list):
        for item in data:
            yield from find_resource_types(item)