"""
シナリオ管理のサービス層
"""
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
            response = self.table.scan(
                FilterExpression=Attr("PK").begins_with("scenario#") & Attr("SK").eq("metadata")
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
                    'PK': f'scenario#{scenario_id}',
                    'SK': 'metadata'
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
                'features': item.get('features', [])
            }
            
            # リクエストデータを取得（オプション）
            if include_requests:
                request_response = self.table.query(
                    KeyConditionExpression=Key("PK").eq(f'scenario#{scenario_id}') & Key("SK").begins_with("request#")
                )
                
                requests = []
                for request_item in request_response.get('Items', []):
                    request_item = convert_decimal_to_int(request_item)
                    monthly_request = {
                        'month': request_item.get('month', 0),
                        'feature': request_item.get('feature', []),
                        'funds': request_item.get('funds', 0),
                        'description': request_item.get('description', '')
                    }
                    requests.append(monthly_request)
                
                # 月順でソート
                requests.sort(key=lambda x: x['month'])
                scenario_data['requests'] = requests
            
            return Scenario(**scenario_data)
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"シナリオ取得エラー: {str(e)}")
    
    async def get_month_data(self, scenario_id: str, month: int) -> MonthData:
        """指定された月のシナリオデータを取得"""
        try:
            response = self.table.get_item(
                Key={
                    'PK': f'scenario#{scenario_id}',
                    'SK': f'request#{month:03d}'
                }
            )
            
            item = response.get('Item')
            if not item:
                raise HTTPException(status_code=404, detail=f"月 {month} のデータが見つかりません")
            
            # Decimal型をintに変換
            item = convert_decimal_to_int(item)
            
            return MonthData(
                scenario_id=item.get('scenario_id', ''),
                month=item.get('month', 0),
                feature=item.get('feature', []),
                funds=item.get('funds', 0),
                description=item.get('description', '')
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"月データ取得エラー: {str(e)}")
    
    async def get_feature_by_id(self, feature_id: str) -> FeatureDetail:
        """指定されたフィーチャーの詳細を取得"""
        try:
            response = self.table.get_item(
                Key={
                    'PK': f'feature#{feature_id}',
                    'SK': 'metadata'
                }
            )
            
            item = response.get('Item')
            if not item:
                raise HTTPException(status_code=404, detail="フィーチャーが見つかりません")
            
            return FeatureDetail(
                feature_id=item.get('feature_id', ''),
                scenario_id=item.get('scenario_id', ''),
                type=item.get('type', ''),
                feature=item.get('feature', ''),
                required=item.get('required', []),
                created_at=item.get('created_at', '')
            )
            
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
