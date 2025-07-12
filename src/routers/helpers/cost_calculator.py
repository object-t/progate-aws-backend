from decimal import Decimal
from typing import Dict, Any, Tuple
from routers.costs import get_costs


def convert_struct_for_cost_calculation(struct_data):
    """
    複雑なstructデータをコスト計算しやすい形式に変換する
    """
    if not struct_data:
        return {}

    converted = {}

    # 既にシンプルな形式の場合はそのまま返す
    if all(
        isinstance(v, (dict, int, float)) and not isinstance(v, list)
        for v in struct_data.values()
    ):
        # トップレベルがサービス名の場合
        if any(
            key.lower()
            in [
                "ec2",
                "rds",
                "s3",
                "lambda",
                "vpc",
                "nat_gateway",
                "elastic_ip",
                "dynamo_db",
            ]
            for key in struct_data.keys()
        ):
            return struct_data

    # 複雑な構造の場合は変換処理を実行
    try:
        # VPCの処理
        if "vpc" in struct_data:
            converted["vpc"] = {"quantity": 1}

        # Availability Zonesの処理
        if "availabilityZones" in struct_data:
            az_count = len(struct_data["availabilityZones"])
            if az_count > 0:
                converted["availability_zone"] = {"quantity": az_count}

        # Subnetsの処理
        if "subnets" in struct_data:
            subnet_types = {}
            for subnet in struct_data["subnets"]:
                subnet_type = subnet.get("type", "subnet")
                if subnet_type in subnet_types:
                    subnet_types[subnet_type] += 1
                else:
                    subnet_types[subnet_type] = 1

            for subnet_type, count in subnet_types.items():
                converted[subnet_type] = {"quantity": count}

        # Networksの処理
        if "networks" in struct_data:
            network_types = {}
            for network in struct_data["networks"]:
                network_type = network.get("type", "network")
                if network_type in network_types:
                    network_types[network_type] += 1
                else:
                    network_types[network_type] = 1

            for network_type, count in network_types.items():
                converted[network_type] = {"quantity": count}

        # Computesの処理
        if "computes" in struct_data:
            compute_types = {}
            elastic_ip_count = 0

            for compute in struct_data["computes"]:
                compute_type = compute.get("type", "compute")
                if compute_type in compute_types:
                    compute_types[compute_type] += 1
                else:
                    compute_types[compute_type] = 1

                # Elastic IPの数もカウント
                if "elasticIpId" in compute:
                    elastic_ip_count += 1

            for compute_type, count in compute_types.items():
                converted[compute_type] = {"quantity": count}

            if elastic_ip_count > 0:
                converted["elastic_ip"] = {"quantity": elastic_ip_count}

        # Databasesの処理
        if "databases" in struct_data:
            database_types = {}
            for database in struct_data["databases"]:
                database_type = database.get("type", "database")
                if database_type in database_types:
                    database_types[database_type] += 1
                else:
                    database_types[database_type] = 1

            for database_type, count in database_types.items():
                converted[database_type] = {"quantity": count}

        # 配列形式の場合の処理
        if isinstance(struct_data, list):
            for item in struct_data:
                if isinstance(item, dict):
                    sub_converted = convert_struct_for_cost_calculation(item)
                    for key, value in sub_converted.items():
                        if key in converted:
                            if isinstance(converted[key], dict) and isinstance(
                                value, dict
                            ):
                                converted[key]["quantity"] = converted[key].get(
                                    "quantity", 0
                                ) + value.get("quantity", 0)
                        else:
                            converted[key] = value

        return converted if converted else struct_data

    except Exception as e:
        print(f"struct変換エラー: {e}")
        # エラーが発生した場合は元のデータを返す
        return struct_data if isinstance(struct_data, dict) else {}


async def calculate_infrastructure_cost(
    struct_data: Dict[str, Any], month_requests: int = 0
) -> Tuple[Decimal, Dict[str, Decimal]]:
    """
    インフラストラクチャのコストを計算する

    Args:
        struct_data: インフラストラクチャの構造データ
        month_requests: 月間リクエスト数

    Returns:
        Tuple[Decimal, Dict[str, Decimal]]: (総コスト, リソース別コスト)
    """
    # structデータをコスト計算用に変換
    converted_struct_data = convert_struct_for_cost_calculation(struct_data)

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

    return total_cost, resource_costs


def check_game_over(total_cost: Decimal, current_funds: Decimal) -> bool:
    """
    ゲームオーバー判定を行う

    Args:
        total_cost: 総コスト
        current_funds: 現在の資金

    Returns:
        bool: ゲームオーバーかどうか
    """
    return total_cost > current_funds if current_funds > 0 else False
