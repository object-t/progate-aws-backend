from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal


class Feature(BaseModel):
    """フィーチャーモデル"""

    id: str
    type: str
    feature: str
    required: List[str]


class RequestFeature(BaseModel):
    """リクエストフィーチャーモデル"""

    feature_id: str
    request: Optional[int] = None


class MonthlyRequest(BaseModel):
    """月別リクエストモデル"""

    month: int
    feature: List[RequestFeature]
    funds: int
    description: str


class Scenario(BaseModel):
    """シナリオモデル"""

    scenario_id: str
    name: str
    end_month: int
    current_month: int
    features: List[Feature]
    requests: Optional[List[MonthlyRequest]] = None


class ScenarioSummary(BaseModel):
    """シナリオサマリーモデル"""

    scenario_id: str
    name: str
    end_month: int
    current_month: int
    feature_count: int
    created_at: Optional[str] = None


class FeatureDetail(BaseModel):
    """フィーチャー詳細モデル"""

    feature_id: str
    scenario_id: str
    type: str
    feature: str
    required: List[str]
    created_at: Optional[str] = None


class MonthData(BaseModel):
    """月データモデル"""

    scenario_id: str
    month: int
    feature: List[RequestFeature]
    funds: int
    description: str


class CostCalculationResult(BaseModel):
    """コスト計算結果モデル"""

    scenario_id: str
    month: int
    total_requests: int
    budget: float
    calculated_cost: float
    budget_remaining: float
    is_over_budget: bool
    features_used: List[str]
    description: str


def convert_decimal_to_int(obj):
    """Decimal型をintに変換するヘルパー関数"""
    if isinstance(obj, dict):
        return {k: convert_decimal_to_int(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimal_to_int(item) for item in obj]
    elif isinstance(obj, Decimal):
        return int(obj)
    else:
        return obj
