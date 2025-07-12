from fastapi import APIRouter, Query
from typing import List
from models.scenario import Scenario, ScenarioSummary, FeatureDetail, MonthData, CostCalculationResult
from scenario.service import scenario_service

scenarios_router = APIRouter()

@scenarios_router.get("/scenarios", response_model=List[ScenarioSummary])
async def get_scenarios():
    """全シナリオの一覧を取得"""
    return await scenario_service.get_all_scenarios()

@scenarios_router.get("/scenarios/{scenario_id}", response_model=Scenario)
async def get_scenario(
    scenario_id: str, 
    include_requests: bool = Query(True, description="リクエストデータを含めるかどうか")
):
    """指定されたシナリオの詳細を取得"""
    return await scenario_service.get_scenario_by_id(scenario_id, include_requests)

@scenarios_router.get("/scenarios/{scenario_id}/month/{month}", response_model=MonthData)
async def get_scenario_month_data(scenario_id: str, month: int):
    """指定された月のシナリオデータを取得"""
    return await scenario_service.get_month_data(scenario_id, month)

@scenarios_router.get("/features/{feature_id}", response_model=FeatureDetail)
async def get_feature(feature_id: str):
    """指定されたフィーチャーの詳細を取得"""
    return await scenario_service.get_feature_by_id(feature_id)

@scenarios_router.get("/scenarios/{scenario_id}/calculate-cost/{month}", response_model=CostCalculationResult)
async def calculate_scenario_cost(scenario_id: str, month: int):
    """指定された月のシナリオコストを計算"""
    return await scenario_service.calculate_scenario_cost(scenario_id, month)
