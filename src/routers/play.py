from fastapi import APIRouter, Depends, HTTPException
import models.play as play_models
import boto3
from boto3.dynamodb.conditions import Key, Attr
import uuid
import json
from datetime import datetime
<<<<<<< HEAD
from settings import get_BedrockSettings, get_DynamoDbSettings
=======
from decimal import Decimal
from settings import get_DynamoDbConnect
>>>>>>> 956518e (fix: /play/report)
from routers.extractor import extract_user_id_from_token
from routers.costs import get_costs, calculate_final_cost
from routers.helpers.service import scenario_service
from typing import List

def convert_struct_for_cost_calculation(struct_data):
    """
    複雑なstructデータをコスト計算しやすい形式に変換する
    """
    if not struct_data:
        return {}
    
    converted = {}
    
    # 既にシンプルな形式の場合はそのまま返す
    if all(isinstance(v, (dict, int, float)) and not isinstance(v, list) for v in struct_data.values()):
        # トップレベルがサービス名の場合
        if any(key.lower() in ['ec2', 'rds', 's3', 'lambda', 'vpc', 'nat_gateway', 'elastic_ip', 'dynamo_db'] for key in struct_data.keys()):
            return struct_data
    
    # 複雑な構造の場合は変換処理を実行
    try:
        # VPCの処理
        if 'vpc' in struct_data:
            converted['vpc'] = {'quantity': 1}
        
        # Availability Zonesの処理
        if 'availabilityZones' in struct_data:
            az_count = len(struct_data['availabilityZones'])
            if az_count > 0:
                converted['availability_zone'] = {'quantity': az_count}
        
        # Subnetsの処理
        if 'subnets' in struct_data:
            subnet_types = {}
            for subnet in struct_data['subnets']:
                subnet_type = subnet.get('type', 'subnet')
                if subnet_type in subnet_types:
                    subnet_types[subnet_type] += 1
                else:
                    subnet_types[subnet_type] = 1
            
            for subnet_type, count in subnet_types.items():
                converted[subnet_type] = {'quantity': count}
        
        # Networksの処理
        if 'networks' in struct_data:
            network_types = {}
            for network in struct_data['networks']:
                network_type = network.get('type', 'network')
                if network_type in network_types:
                    network_types[network_type] += 1
                else:
                    network_types[network_type] = 1
            
            for network_type, count in network_types.items():
                converted[network_type] = {'quantity': count}
        
        # Computesの処理
        if 'computes' in struct_data:
            compute_types = {}
            elastic_ip_count = 0
            
            for compute in struct_data['computes']:
                compute_type = compute.get('type', 'compute')
                if compute_type in compute_types:
                    compute_types[compute_type] += 1
                else:
                    compute_types[compute_type] = 1
                
                # Elastic IPの数もカウント
                if 'elasticIpId' in compute:
                    elastic_ip_count += 1
            
            for compute_type, count in compute_types.items():
                converted[compute_type] = {'quantity': count}
            
            if elastic_ip_count > 0:
                converted['elastic_ip'] = {'quantity': elastic_ip_count}
        
        # Databasesの処理
        if 'databases' in struct_data:
            database_types = {}
            for database in struct_data['databases']:
                database_type = database.get('type', 'database')
                if database_type in database_types:
                    database_types[database_type] += 1
                else:
                    database_types[database_type] = 1
            
            for database_type, count in database_types.items():
                converted[database_type] = {'quantity': count}
        
        # 配列形式の場合の処理
        if isinstance(struct_data, list):
            for item in struct_data:
                if isinstance(item, dict):
                    sub_converted = convert_struct_for_cost_calculation(item)
                    for key, value in sub_converted.items():
                        if key in converted:
                            if isinstance(converted[key], dict) and isinstance(value, dict):
                                converted[key]['quantity'] = converted[key].get('quantity', 0) + value.get('quantity', 0)
                        else:
                            converted[key] = value
        
        return converted if converted else struct_data
        
    except Exception as e:
        print(f"struct変換エラー: {e}")
        # エラーが発生した場合は元のデータを返す
        return struct_data if isinstance(struct_data, dict) else {}


play_router = APIRouter()
<<<<<<< HEAD
bedrocksettings = get_BedrockSettings()
dynamodbsettings = get_DynamoDbSettings()

BEDROCK_REGION = bedrocksettings.BEDROCK_REGION
REGION = dynamodbsettings.REGION
=======

settings = get_DynamoDbConnect()

DYNAMODB_ENDPOINT = settings.DYNAMODB_ENDPOINT
REGION = settings.REGION
AWS_ACCESS_KEY_ID = settings.AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY = settings.AWS_SECRET_ACCESS_KEY
>>>>>>> 956518e (fix: /play/report)

dynamodb = boto3.resource(
    "dynamodb",
    region_name=REGION,

)

table_name = "game"
table = dynamodb.Table(table_name)

@play_router.get("/play/scenarioes")
async def get_scenarioes(user_id: str = Depends(extract_user_id_from_token)):
    response = table.query(
        KeyConditionExpression=Key("PK").eq("scenario")
    )
    response_items = response.get("Items", [])
    return response_items

@play_router.post("/play/create")
<<<<<<< HEAD
async def create_game(request: play_models.CreateGameRequest, user_id: str = Depends(extract_user_id_from_token)) -> play_models.CreateGameResponse:
=======
# async def create_game(request: play_models.CreateGameRequest, user_id: str = Depends(extract_user_id_from_token)) -> play_models.CreateGameResponse:
async def create_game(request: play_models.CreateGameRequest, user_id: str) -> play_models.CreateGameResponse:
>>>>>>> 956518e (fix: /play/report)
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
    """ゲームのレポートを生成"""
    try:
        formatted_user_id = f"user#{user_id}"
        formatted_game_id = f"game#{game_id}"
        
        response = table.query(
            KeyConditionExpression=Key("PK").eq(formatted_user_id) & Key("SK").eq(formatted_game_id)
        )
        
        items = response.get("Items", [])
        if not items:
            raise HTTPException(status_code=404, detail="ゲームが見つかりません")
        
        game_data = items[0]
        struct_data = game_data.get("struct", {})
        current_month = game_data.get("current_month", 0)
        scenario_name = game_data.get("scenarioes", "")
        current_funds = game_data.get("funds", 0)

        # structデータをコスト計算用に変換
        converted_struct_data = convert_struct_for_cost_calculation(struct_data)

        # シナリオ一覧を取得
        scenarios = await get_scenarioes(user_id)
        
        # シナリオ名に基づいて対応するシナリオを検索
        target_scenario = None
        for scenario in scenarios:
            scenario_name_to_check = scenario.name if hasattr(scenario, 'name') else scenario.get('name', '')
            if scenario_name in scenario_name_to_check or scenario_name_to_check in scenario_name:
                target_scenario = scenario
                break
        
        if not target_scenario:
            available_scenarios = [s.name if hasattr(s, 'name') else s.get('name', 'Unknown') for s in scenarios]
            raise HTTPException(status_code=404, detail=f"シナリオが見つかりません: {scenario_name}. 利用可能: {available_scenarios}")

        # シナリオの詳細データを取得（リクエスト情報を含む）
        scenario_id = target_scenario.scenario_id if hasattr(target_scenario, 'scenario_id') else target_scenario.get('scenario_id', '')
        scenario_detail = await scenario_service.get_scenario_by_id(
            scenario_id, 
            include_requests=True
        )
        
        if not scenario_detail:
            raise HTTPException(status_code=404, detail="シナリオ詳細が見つかりません")

        # 現在の月のリクエスト数を取得
        month_requests = 0
        for request_data in scenario_detail.requests:
            if request_data.get("month") == current_month:
                for feature in request_data.get("feature", []):
                    if isinstance(feature, dict) and "request" in feature:
                        month_requests += feature["request"]
                break

        # コストデータを取得
        costs_db = await get_costs()
        
        # per_monthコスト計算と各リソースごとのコスト追跡
        per_month_cost = Decimal('0.0')
        resource_costs = {}
        
        for service_name, service_config in converted_struct_data.items():
            service_name_lower = service_name.lower()
            if service_name_lower in costs_db:
                cost_info = costs_db[service_name_lower]
                if cost_info.get("type") == "per_month":
                    # サービス設定に基づいてコスト計算
                    base_cost = Decimal(str(cost_info.get("cost", 0.0)))
                    if isinstance(service_config, dict):
                        quantity = Decimal(str(service_config.get("quantity", 1)))
                        service_total_cost = base_cost * quantity
                    else:
                        service_total_cost = base_cost
                    
                    per_month_cost += service_total_cost
                    resource_costs[service_name] = service_total_cost

        # per_requestsコスト計算
        per_requests_cost = Decimal('0.0')
        for service_name, service_config in converted_struct_data.items():
            service_name_lower = service_name.lower()
            if service_name_lower in costs_db:
                cost_info = costs_db[service_name_lower]
                if cost_info.get("type") == "per_request":
                    # リクエスト数に基づいてコスト計算
                    cost_per_request = Decimal(str(cost_info.get("cost", 0.0)))
                    month_requests_decimal = Decimal(str(month_requests))
                    if isinstance(service_config, dict):
                        multiplier = Decimal(str(service_config.get("multiplier", 1.0)))
                        service_total_cost = cost_per_request * month_requests_decimal * multiplier
                    else:
                        service_total_cost = cost_per_request * month_requests_decimal
                    
                    per_requests_cost += service_total_cost
                    # per_requestタイプのコストも各リソースに追加
                    if service_name in resource_costs:
                        resource_costs[service_name] += service_total_cost
                    else:
                        resource_costs[service_name] = service_total_cost

        # 総コスト計算
        total_cost = per_month_cost + per_requests_cost
        
        # ゲームオーバー判定
        scenario_funds = Decimal(str(current_funds))
        game_over = total_cost > scenario_funds if scenario_funds > 0 else False

        return {
            "total_cost": total_cost,
            "resource_costs": resource_costs,
            "game_over": game_over
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"レポート生成エラー: {str(e)}")

@play_router.post("/play/ai/{game_id}")
async def get_advice_from_ai(
    game_id: str,
    user_id: str = Depends(extract_user_id_from_token)
):
    """AIからのアドバイスを取得"""
    try:
        formatted_user_id = f"user#{user_id}"

        response = table.query(
            KeyConditionExpression=Key("PK").eq(formatted_user_id)
            & Key("SK").begins_with("game"),
            FilterExpression=Attr("is_finished").eq(False),
            ProjectionExpression="struct"
        )
        
        items = response.get("Items", [])
        if not items:
            raise HTTPException(status_code=404, detail="進行中のゲームが見つかりません")
        
        struct = items[0].get("struct", {})

<<<<<<< HEAD
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
=======
        struct_json = json.dumps(struct, indent=2, ensure_ascii=False)
        prompt = f"あなたは、AWSのエキスパートです。この構造について何かアドバイスをして欲しいです：\n\n{struct_json}\n\nその際に、メンズコーチジョージのような口調で答えてください。"

        try:
            bedrock = boto3.client(
                service_name="bedrock-runtime",
                region_name=REGION,
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY
            )
>>>>>>> 956518e (fix: /play/report)

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
            return {"advice": answer}
        except Exception as bedrock_error:
            # Bedrockが利用できない場合のフォールバック
            return {
                "advice": "申し訳ございませんが、現在AIアドバイス機能は利用できません。後ほど再度お試しください。",
                "error": "Bedrock service unavailable"
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AIアドバイス取得エラー: {str(e)}")

@play_router.put("/play/{game_id}")
async def update_game(game_id: str, request: play_models.UpdateGameRequest, user_id: str = "test-user-123"):
    """ゲームデータを更新"""
    try:
        pk = f"user#{user_id}"
        sk = f"game#{game_id}"

        table.update_item(
            Key={"PK": pk, "SK": sk},
            UpdateExpression="SET #struct = :data",
            ExpressionAttributeNames={"#struct": "struct"},
            ExpressionAttributeValues={":data": request.data}
        )

        return {"message": "Game data updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ゲーム更新エラー: {str(e)}")


