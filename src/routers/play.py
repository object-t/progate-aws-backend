from fastapi import APIRouter, Depends, HTTPException
import models.play as play_models
import boto3
from boto3.dynamodb.conditions import Key, Attr
import uuid
import json
from decimal import Decimal
from datetime import datetime
from settings import get_BedrockSettings, get_DynamoDbSettings
from routers.extractor import extract_user_id_without_verification
from routers.costs import get_costs, calculate_final_cost
from routers.helpers.service import scenario_service
from typing import List


def convert_struct_for_cost_calculation(struct_data):
    """
    複雑なstructデータをコスト計算用の簡素な形式に変換する
    costs.jsonのキーに対応する形式: {service_name: {quantity: count}}
    """
    if not struct_data:
        return {}
      
    # 既にシンプルな形式（costs.jsonのキーが直接使われている）の場合はそのまま返す
    if isinstance(struct_data, dict) and all(
        isinstance(v, (dict, int, float)) and not isinstance(v, list)
        for v in struct_data.values()
    ):
        # costs.jsonに存在するサービス名かチェック
        cost_service_names = [
            "rds",
            "s3",
            "dynamo_db",
            "nat_gateway",
            "vpc",
            "cloudfront",
            "elastic_ip",
            "public_subnet",
            "route53",
            "lambda",
            "endpoint",
            "cost_explorer",
            "alb",
            "api_gateway",
            "private_subnet",
        ]
        if any(key.lower() in cost_service_names for key in struct_data.keys()):
            return struct_data

    # 複雑な構造から簡素な形式に変換
    converted = {}

    try:
        # VPC構造の処理
        if "vpc" in struct_data and isinstance(struct_data["vpc"], list):
            for vpc_item in struct_data["vpc"]:
                # VPC自体（無料だが数をカウント）
                converted["vpc"] = {"quantity": 1}

                # データベース（RDS）
                if "databases" in vpc_item:
                    rds_count = 0
                    for db in vpc_item["databases"]:
                        if db.get("type") == "rds":
                            rds_count += 1
                            # Read Replicaも追加
                            if (
                                "replication" in db
                                and "readReplicas" in db["replication"]
                            ):
                                rds_count += len(db["replication"]["readReplicas"])
                    if rds_count > 0:
                        converted["rds"] = {"quantity": rds_count}

                # コンピュートリソース
                if "computes" in vpc_item:
                    lambda_count = 0
                    alb_count = 0
                    for compute in vpc_item["computes"]:
                        if compute.get("type") == "lambda":
                            lambda_count += 1
                        elif compute.get("type") == "alb":
                            alb_count += 1

                    if lambda_count > 0:
                        converted["lambda"] = {"quantity": lambda_count}
                    if alb_count > 0:
                        converted["alb"] = {"quantity": alb_count}

                # ネットワークリソース
                if "networks" in vpc_item:
                    nat_gateway_count = 0
                    endpoint_count = 0
                    for network in vpc_item["networks"]:
                        if network.get("type") == "nat_gateway":
                            nat_gateway_count += 1
                        elif network.get("type") == "endpoint":
                            endpoint_count += 1

                    if nat_gateway_count > 0:
                        converted["nat_gateway"] = {"quantity": nat_gateway_count}
                    if endpoint_count > 0:
                        converted["endpoint"] = {"quantity": endpoint_count}

                # サブネット
                if "subnets" in vpc_item:
                    public_subnet_count = 0
                    private_subnet_count = 0
                    for subnet in vpc_item["subnets"]:
                        if subnet.get("type") == "public_subnet":
                            public_subnet_count += 1
                        elif subnet.get("type") == "private_subnet":
                            private_subnet_count += 1

                    if public_subnet_count > 0:
                        converted["public_subnet"] = {"quantity": public_subnet_count}
                    if private_subnet_count > 0:
                        converted["private_subnet"] = {"quantity": private_subnet_count}

        # リージョナルリソース
        if "rigional" in struct_data and isinstance(struct_data["rigional"], list):
            for resource in struct_data["rigional"]:
                resource_type = resource.get("type")

                # costs.jsonのキーに直接マッピング
                if resource_type == "s3":
                    converted["s3"] = converted.get("s3", {"quantity": 0})
                    converted["s3"]["quantity"] += 1
                elif resource_type == "api_gateway":
                    converted["api_gateway"] = converted.get(
                        "api_gateway", {"quantity": 0}
                    )
                    converted["api_gateway"]["quantity"] += 1
                elif resource_type == "route53":
                    converted["route53"] = converted.get("route53", {"quantity": 0})
                    converted["route53"]["quantity"] += 1
                elif resource_type == "cloudfront":
                    converted["cloudfront"] = converted.get(
                        "cloudfront", {"quantity": 0}
                    )
                    converted["cloudfront"]["quantity"] += 1
                elif resource_type == "elastic_ip":
                    converted["elastic_ip"] = converted.get(
                        "elastic_ip", {"quantity": 0}
                    )
                    converted["elastic_ip"]["quantity"] += 1

        return converted


    except Exception as e:
        print(f"Struct conversion error: {e}")
        return {}

play_router = APIRouter()
bedrocksettings = get_BedrockSettings()
dynamodbsettings = get_DynamoDbSettings()

BEDROCK_REGION = bedrocksettings.BEDROCK_REGION
REGION = dynamodbsettings.REGION


region = "ap-northeast-1"

dynamodb = boto3.resource("dynamodb", region_name=region)

table_name = "game"
table = dynamodb.Table(table_name)


@play_router.get("/play/test")
async def get_test():
    return table


@play_router.get("/play/scenarioes")
async def get_scenarioes(user_id: str = Depends(extract_user_id_without_verification)):
    response = table.query(
        KeyConditionExpression=Key("PK").eq("scenario")
    )
    response_items = response.get("Items", [])
    return response_items


@play_router.post("/play/create")
async def create_game(request: play_models.CreateGameRequest, user_id: str = Depends(extract_user_id_without_verification)) -> play_models.CreateGameResponse:
    scenario_id = request.scenario_id
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
        "scenario_id": scenario_id,
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
        "scenario_id": game_item["scenario_id"],
        "is_finished": game_item["is_finished"],
        "created_at": game_item["created_at"],
    }

    return play_models.CreateGameResponse(**formatted_response)


@play_router.get("/play/games")
async def get_game(
    user_id: str = Depends(extract_user_id_without_verification),
) -> play_models.GetGameResponse:
    formatted_user_id = f"user#{user_id}"

    response = table.query(
        KeyConditionExpression=Key("PK").eq(formatted_user_id)
        & Key("SK").begins_with("game"),
        FilterExpression=Attr("is_finished").eq(False),
    )

    length = len(response["Items"])
    if length == 0:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")
    
    game_data = response["Items"][0]
    
    formatted_response = {
        "user_id": game_data.get("PK", "").replace("user#", ""),
        "game_id": game_data.get("SK", "").replace("game#", ""),
        "struct": game_data.get("struct"),
        "funds": game_data.get("funds"),
        "current_month": game_data.get("current_month"),
        "scenario_id": game_data.get("scenario_id", ""),
        "is_finished": game_data.get("is_finished"),
        "created_at": game_data.get("created_at"),
    }

    return play_models.GetGameResponse(**formatted_response)


@play_router.post("/play/report/{game_id}")
async def report_game(
    game_id: str, user_id: str = Depends(extract_user_id_without_verification)
):
    """ゲームのレポートを生成"""
    try:
        formatted_user_id = f"user#{user_id}"
        formatted_game_id = f"game#{game_id}"

        response = table.query(
            KeyConditionExpression=Key("PK").eq(formatted_user_id)
            & Key("SK").eq(formatted_game_id)
        )

        items = response.get("Items", [])
        if not items:
            raise HTTPException(status_code=404, detail="ゲームが見つかりません")

        game_data = items[0]
        struct_data = game_data.get("struct", {})
        current_month = game_data.get("current_month", 0)
        scenario_name = game_data.get("scenario_id", "")
        current_funds = game_data.get("funds", 0)

        # structデータをコスト計算用に変換
        converted_struct_data = convert_struct_for_cost_calculation(struct_data)

        # シナリオ一覧を取得
        response = table.query(KeyConditionExpression=Key("PK").eq("scenario"))
        scenarios = response.get("Items", [])

        # シナリオIDに基づいて対応するシナリオを検索
        target_scenario = None
        for scenario in scenarios:
            scenario_id_to_check = (
                scenario.scenario_id if hasattr(scenario, "scenario_id") else scenario.get("scenario_id", "")
            )
            if scenario_id_to_check == scenario_name:
                target_scenario = scenario
                break

        if not target_scenario:
            available_scenarios = [
                s.scenario_id if hasattr(s, "scenario_id") else s.get("scenario_id", "Unknown")
                for s in scenarios
            ]
            raise HTTPException(
                status_code=404,
                detail=f"シナリオが見つかりません: {scenario_name}. 利用可能: {available_scenarios}",
            )

        # シナリオの詳細データを取得（リクエスト情報を含む）
        scenario_id = (
            target_scenario.scenario_id
            if hasattr(target_scenario, "scenario_id")
            else target_scenario.get("scenario_id", "")
        )
        scenario_detail = await scenario_service.get_scenario_by_id(
            scenario_id, include_requests=True
        )

        if not scenario_detail:
            raise HTTPException(status_code=404, detail="シナリオ詳細が見つかりません")

        # 現在の月のリクエスト数を取得
        month_requests = 0
        for request_data in scenario_detail.requests:
            if request_data.month == current_month:
                for feature in request_data.feature:
                    if hasattr(feature, 'request') and feature.request is not None:
                        month_requests += feature.request
                break

        # コストデータを取得
        costs_db = await get_costs()

        # per_monthコスト計算と各リソースごとのコスト追跡
        per_month_cost = Decimal("0.0")
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
        per_requests_cost = Decimal("0.0")
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
                        service_total_cost = (
                            cost_per_request * month_requests_decimal * multiplier
                        )
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
            "game_over": game_over,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"レポート生成エラー: {str(e)}")


@play_router.post("/play/ai")
async def get_advice_from_ai(
    struct: play_models.GetStructResponse, user_id: str = Depends(extract_user_id_without_verification)
):

    # Pydanticモデルを辞書に変換してからJSON化
    struct_dict = struct.dict() if hasattr(struct, 'dict') else struct.__dict__
    struct_json = json.dumps(struct_dict, indent=2, ensure_ascii=False)
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
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
            "temperature": 0.1,
            "top_p": 0.9,
            "anthropic_version": "bedrock-2023-05-31",
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


@play_router.put("/play/{game_id}")
async def update_game(
    game_id: str,
    request: play_models.UpdateGameRequest,
    user_id: str = Depends(extract_user_id_without_verification),
):
    """ゲームデータを更新"""
    try:
        pk = f"user#{user_id}"
        sk = f"game#{game_id}"

        table.update_item(
            Key={"PK": pk, "SK": sk},
            UpdateExpression="SET #struct = :data",
            ExpressionAttributeNames={"#struct": "struct"},
            ExpressionAttributeValues={":data": request.data},
        )

        return {"message": "Game data updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ゲーム更新エラー: {str(e)}")
