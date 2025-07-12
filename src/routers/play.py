from fastapi import APIRouter, Depends
import models.play as play_models
import boto3
from boto3.dynamodb.conditions import Key, Attr
import uuid
import json
from datetime import datetime
from settings import get_BedrockSettings, get_DynamoDbConnect
from routers.extractor import extract_user_id_from_token
from routers.costs import get_costs, calculate_final_cost
import json

play_router = APIRouter()
bedrocksettings = get_BedrockSettings()
dynamodbsettings = get_DynamoDbConnect()

BEDROCK_REGION = bedrocksettings.BEDROCK_REGION
REGION = dynamodbsettings.REGION

dynamodb = boto3.resource(
    "dynamodb",
    region_name=REGION,
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
async def create_game(request: play_models.CreateGameRequest, user_id: str = Depends(extract_user_id_from_token)) -> play_models.CreateGameResponse:
    scenarioes = request.scenarioes
    game_name = request.game_name

    game_id = str(uuid.uuid4())
    sandbox_id = str(uuid.uuid4())

    game_item = {
        "PK": f"user#{user_id}",
        "SK": f"game#{game_id}",
        "game_name": game_name,
        "struct": None,
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
        "game_name": game_name,
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
async def report_game(game_id: str, user_id: str = "test-user-123"):
    formatted_user_id = f"user#{user_id}"
    formatted_game_id = f"game#{game_id}"
    response = table.query(
        KeyConditionExpression=Key("PK").eq(formatted_user_id) & Key("SK").begins_with(formatted_game_id)
    )
    game_data = response.get("Items", [{}])[0]
    struct_data = game_data.get("struct", {})
    current_month = game_data.get("current_month", 0)
    scenario_name = game_data.get("scenarioes", "")

    # シナリオファイルを読み込み
    scenario_data = None
    if scenario_name == "個人ブログ":
        with open("/app/personal_blog_scenario.json", "r", encoding="utf-8") as f:
            scenario_data = json.load(f)
    else:
        with open("/app/scenarioes.json", "r", encoding="utf-8") as f:
            scenario_data = json.load(f)

    # 現在の月のリクエスト数を取得
    total_requests = 0
    if scenario_data and "requests" in scenario_data:
        for request_data in scenario_data["requests"]:
            if request_data["month"] == current_month:
                for feature in request_data.get("feature", []):
                    if "request" in feature:
                        total_requests += feature["request"]
                break

    costs_db = await get_costs()
    final_cost = calculate_final_cost(struct_data, costs_db, total_requests)

    return {
        "message": "Report processed", 
        "calculated_cost": final_cost,
        "current_month": current_month,
        "total_requests": total_requests
    }

@play_router.post("/play/ai/{game_id}")
async def get_advice_from_ai(game_id: str, user_id: str = Depends(extract_user_id_from_token)):
    formatted_user_id = f"user#{user_id}"

    response = table.query(
        KeyConditionExpression=Key("PK").eq(formatted_user_id)
        & Key("SK").begins_with("game"),
        FilterExpression=Attr("is_finished").eq(False)
    )
    game_data = response.get("Items", [{}])[0]
    struct = game_data.get("struct", {})

    struct_json = json.dumps(struct, indent=2, ensure_ascii=False)
    prompt = f"""
        あなたはAWS Bedrockのマジエキスパートです。
        今からマジで構造見せるから、ガチで“危機感持って”厳しくアドバイスをください：

        {struct_json}

        - 無駄ってことない？
        - この設計、お前最後に見直したのいつ？
        - セキュリティとか可用性、甘く見てるんじゃない？
        - レイテンシ最適化とか、Guardrails使ってる？
        - リトリーバルやファインチューンの戦略、甘いって。
        - ここ直さないとあとで地獄見るぞ。

        親友としてガチで叱って、でも腹落ちするように助けてくれ。
        ヤバいくらい“刺さる”口調で頼む。
        """

    bedrock = boto3.client(
        service_name="bedrock-runtime",
        region_name=BEDROCK_REGION,
    )

    body = json.dumps(
        {
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 500,
            "temperature": 0.1,
            "top_p": 0.9,
            "anthropic_version": "bedrock-2023-05-31"
        }
    )

    modelId = "us.anthropic.claude-sonnet-4-20250514-v1:0"
    accept = "application/json"
    contentType = "application/json"

    response = bedrock.invoke_model(
        body=body, modelId=modelId, accept=accept, contentType=contentType
    )

    response_body = json.loads(response.get("body").read())
    answer = response_body["content"][0]["text"]
    return answer

@play_router.put("/play/{game_id}")
async def update_game(game_id: str, request: play_models.UpdateGameRequest, user_id: str = Depends(extract_user_id_from_token)):
    pk = f"user#{user_id}"
    sk = f"game#{game_id}"

    table.update_item(
        Key={"PK": pk, "SK": sk},
        UpdateExpression="SET #struct = :data",
        ExpressionAttributeNames={"#struct": "struct"},
        ExpressionAttributeValues={":data": request.data}
    )

    return {"message": "Game data updated successfully"}


