"""
シナリオ管理のサービス層
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import boto3
from boto3.dynamodb.conditions import Key, Attr
from fastapi import HTTPException
from typing import List, Optional
from models.scenario import (
    Scenario, ScenarioSummary, Feature, MonthlyRequest, 
    FeatureDetail, MonthData, CostCalculationResult,
    convert_decimal_to_int
)
from settings import get_DynamoDbConnect

class ScenarioService:
    """シナリオ管理サービス"""
    
    def __init__(self):
        settings = get_DynamoDbConnect()
        self.dynamodb = boto3.resource(
            "dynamodb",
            region_name=settings.REGION,
        )
        self.table = self.dynamodb.Table("game")
    
    async def get_all_scenarios(self) -> List[ScenarioSummary]:
        """全シナリオの一覧を取得"""
        try:
            response = self.table.query(
                KeyConditionExpression=Key("PK").eq("scenario")
            )
            
            scenarios = []
            for item in response.get('Items', []):
                scenario_summary = ScenarioSummary(
                    scenario_id=item.get('scenario_id', ''),
                    name=item.get('name', ''),
                    end_month=int(item.get('end_month', 0)),
                    current_month=int(item.get('current_month', 0)),
                    feature_count=len(item.get('features', [])),
                    created_at=item.get('created_at', '')
                )
                scenarios.append(scenario_summary)
            
            return scenarios
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"シナリオ取得エラー: {str(e)}")
    
    async def get_scenario_by_id(self, scenario_id: str, include_requests: bool = True) -> Scenario:
        """指定されたシナリオの詳細を取得"""
        try:
            # メインシナリオデータを取得
            response = self.table.get_item(
                Key={
                    'PK': 'scenario',
                    'SK': scenario_id
                }
            )
            
            item = response.get('Item')
            if not item:
                raise HTTPException(status_code=404, detail="シナリオが見つかりません")
            
            # Decimal型をintに変換
            item = convert_decimal_to_int(item)
            
            scenario_data = {
                'scenario_id': item.get('scenario_id', ''),
                'name': item.get('name', ''),
                'end_month': item.get('end_month', 0),
                'current_month': item.get('current_month', 0),
                'features': item.get('features', []),
                'requests': item.get('requests', []) if include_requests else []
            }
            
            return Scenario(**scenario_data)
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"シナリオ取得エラー: {str(e)}")
    
    async def get_month_data(self, scenario_id: str, month: int) -> MonthData:
        """指定された月のシナリオデータを取得"""
        try:
            # シナリオデータを取得
            response = self.table.get_item(
                Key={
                    'PK': 'scenario',
                    'SK': scenario_id
                }
            )
            
            item = response.get('Item')
            if not item:
                raise HTTPException(status_code=404, detail="シナリオが見つかりません")
            
            # Decimal型をintに変換
            item = convert_decimal_to_int(item)
            
            # 指定された月のリクエストデータを検索
            requests = item.get('requests', [])
            month_request = None
            
            for request in requests:
                if request.get('month') == month:
                    month_request = request
                    break
            
            if not month_request:
                raise HTTPException(status_code=404, detail=f"月 {month} のデータが見つかりません")
            
            return MonthData(
                scenario_id=scenario_id,
                month=month_request.get('month', 0),
                feature=month_request.get('feature', []),
                funds=month_request.get('funds', 0),
                description=month_request.get('description', '')
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"月データ取得エラー: {str(e)}")
    
    async def get_feature_by_id(self, feature_id: str) -> FeatureDetail:
        """指定されたフィーチャーの詳細を取得"""
        try:
            # 全シナリオを検索してフィーチャーを探す
            response = self.table.query(
                KeyConditionExpression=Key("PK").eq("scenario")
            )
            
            for item in response.get('Items', []):
                features = item.get('features', [])
                for feature in features:
                    if feature.get('id') == feature_id:
                        return FeatureDetail(
                            feature_id=feature.get('id', ''),
                            scenario_id=item.get('scenario_id', ''),
                            type=feature.get('type', ''),
                            feature=feature.get('feature', ''),
                            required=feature.get('required', []),
                            created_at=item.get('created_at', '')
                        )
            
            raise HTTPException(status_code=404, detail="フィーチャーが見つかりません")
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"フィーチャー取得エラー: {str(e)}")
    
    async def calculate_scenario_cost(self, scenario_id: str, month: int) -> CostCalculationResult:
        """指定された月のシナリオコストを計算"""
        try:
            # 月データを取得
            month_data = await self.get_month_data(scenario_id, month)
            
            # コスト計算用の構造データを作成
            struct_data = {}
            total_requests = 0
            
            for feature_request in month_data.feature:
                feature_id = feature_request.feature_id
                request_count = feature_request.request or 0
                
                # フィーチャー詳細を取得
                try:
                    feature_detail = await self.get_feature_by_id(feature_id)
                    feature_type = feature_detail.type
                    
                    struct_data[feature_id] = {
                        'type': feature_type,
                        'name': feature_detail.feature
                    }
                    
                    if request_count:
                        total_requests += request_count
                        
                except HTTPException:
                    # フィーチャーが見つからない場合はスキップ
                    continue
            
            # コスト計算APIを呼び出し（内部的に）
            from routers.costs import calculate_final_cost
            
            # コストデータを取得
            costs_response = self.table.query(
                KeyConditionExpression=Key("PK").eq("costs") & Key("SK").begins_with("metadata")
            )
            costs_db = costs_response.get("Items", [{}])[0].get("costs", {})
            
            if not costs_db:
                raise HTTPException(status_code=404, detail="コストデータが見つかりません")
            
            final_cost = calculate_final_cost(struct_data, costs_db, total_requests)
            
            return CostCalculationResult(
                scenario_id=scenario_id,
                month=month,
                total_requests=total_requests,
                budget=float(month_data.funds),
                calculated_cost=final_cost,
                budget_remaining=float(month_data.funds) - final_cost,
                is_over_budget=final_cost > float(month_data.funds),
                features_used=list(struct_data.keys()),
                description=month_data.description
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"コスト計算エラー: {str(e)}")

# シングルトンインスタンス
scenario_service = ScenarioService()
