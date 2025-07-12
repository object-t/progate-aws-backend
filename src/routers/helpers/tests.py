import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
import sys
import os

# 親ディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from main import app

client = TestClient(app)

class TestScenariosAPI:
    """シナリオ管理APIのテストクラス"""
    
    @patch('routers.helpers.service.scenario_service.table')
    def test_get_scenarios_success(self, mock_table):
        """シナリオ一覧取得の成功テスト"""
        mock_table.scan.return_value = {
            "Items": [
                {
                    "scenario_id": "test-001",
                    "name": "テストシナリオ",
                    "end_month": 12,
                    "current_month": 0,
                    "features": [
                        {"id": "f1", "type": "compute", "feature": "Web", "required": ["ec2"]},
                        {"id": "f2", "type": "database", "feature": "DB", "required": ["rds"]}
                    ],
                    "created_at": "2025-07-12T10:00:00"
                }
            ]
        }
        
        response = client.get("/scenarios")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 1
        assert data[0]["scenario_id"] == "test-001"
        assert data[0]["name"] == "テストシナリオ"
        assert data[0]["feature_count"] == 2
    
    @patch('routers.helpers.service.scenario_service.table')
    def test_get_scenario_detail_success(self, mock_table):
        """シナリオ詳細取得の成功テスト"""
        # メインデータのモック
        mock_table.get_item.return_value = {
            "Item": {
                "scenario_id": "test-001",
                "name": "テストシナリオ",
                "end_month": 12,
                "current_month": 0,
                "features": [
                    {"id": "f1", "type": "compute", "feature": "Web", "required": ["ec2"]}
                ]
            }
        }
        
        # リクエストデータのモック
        mock_table.query.return_value = {
            "Items": [
                {
                    "month": 0,
                    "feature": [{"feature_id": "f1", "request": 1000}],
                    "funds": 100,
                    "description": "初月"
                }
            ]
        }
        
        response = client.get("/scenarios/test-001")
        assert response.status_code == 200
        
        data = response.json()
        assert data["scenario_id"] == "test-001"
        assert data["name"] == "テストシナリオ"
        assert len(data["features"]) == 1
        assert len(data["requests"]) == 1
    
    @patch('routers.helpers.service.scenario_service.table')
    def test_get_scenario_not_found(self, mock_table):
        """存在しないシナリオの取得テスト"""
        mock_table.get_item.return_value = {"Item": None}
        
        response = client.get("/scenarios/nonexistent")
        assert response.status_code == 404
        assert "シナリオが見つかりません" in response.json()["detail"]
    
    @patch('routers.helpers.service.scenario_service.table')
    def test_get_scenario_month_data_success(self, mock_table):
        """月別データ取得の成功テスト"""
        mock_table.get_item.return_value = {
            "Item": {
                "scenario_id": "test-001",
                "month": 3,
                "feature": [
                    {"feature_id": "f1", "request": 5000},
                    {"feature_id": "f2", "request": 1000}
                ],
                "funds": 200,
                "description": "3ヶ月目のデータ"
            }
        }
        
        response = client.get("/scenarios/test-001/month/3")
        assert response.status_code == 200
        
        data = response.json()
        assert data["scenario_id"] == "test-001"
        assert data["month"] == 3
        assert data["funds"] == 200
        assert len(data["feature"]) == 2
    
    @patch('routers.helpers.service.scenario_service.table')
    def test_get_feature_success(self, mock_table):
        """フィーチャー詳細取得の成功テスト"""
        mock_table.get_item.return_value = {
            "Item": {
                "feature_id": "f1",
                "scenario_id": "test-001",
                "type": "compute",
                "feature": "Webサーバー",
                "required": ["ec2", "storage"],
                "created_at": "2025-07-12T10:00:00"
            }
        }
        
        response = client.get("/features/f1")
        assert response.status_code == 200
        
        data = response.json()
        assert data["feature_id"] == "f1"
        assert data["type"] == "compute"
        assert data["feature"] == "Webサーバー"
        assert len(data["required"]) == 2

class TestScenarioLogic:
    """シナリオロジックのテストクラス"""
    
    def test_convert_decimal_to_int(self):
        """Decimal変換のテスト"""
        from models.scenario import convert_decimal_to_int
        from decimal import Decimal
        
        test_data = {
            "int_value": Decimal("123"),
            "float_value": Decimal("45.67"),
            "nested": {
                "decimal_list": [Decimal("1"), Decimal("2"), Decimal("3")],
                "string_value": "test"
            }
        }
        
        result = convert_decimal_to_int(test_data)
        
        assert result["int_value"] == 123
        assert result["float_value"] == 45
        assert result["nested"]["decimal_list"] == [1, 2, 3]
        assert result["nested"]["string_value"] == "test"

class TestScenarioIntegration:
    """シナリオ統合テストクラス"""
    
    @patch('routers.helpers.service.scenario_service.table')
    def test_scenario_cost_calculation_integration(self, mock_table):
        """シナリオコスト計算の統合テスト"""
        # 月データのモック
        mock_table.get_item.side_effect = [
            {
                "Item": {
                    "scenario_id": "test-001",
                    "month": 0,
                    "feature": [
                        {"feature_id": "f1", "request": 1000},
                        {"feature_id": "f2"}
                    ],
                    "funds": 50,
                    "description": "初月テスト"
                }
            },
            {
                "Item": {
                    "feature_id": "f1",
                    "scenario_id": "test-001",
                    "type": "compute",
                    "feature": "Webサーバー",
                    "required": ["ec2"]
                }
            },
            {
                "Item": {
                    "feature_id": "f2",
                    "scenario_id": "test-001",
                    "type": "database",
                    "feature": "データベース",
                    "required": ["rds"]
                }
            }
        ]
        
        # コストデータのモック
        mock_table.query.return_value = {
            "Items": [{
                "costs": {
                    "compute": {"cost": "10.00", "type": "per_month"},
                    "database": {"cost": "20.00", "type": "per_month"}
                }
            }]
        }
        
        response = client.get("/scenarios/test-001/calculate-cost/0")
        assert response.status_code == 200
        
        data = response.json()
        assert data["scenario_id"] == "test-001"
        assert data["month"] == 0
        assert data["total_requests"] == 1000
        assert data["budget"] == 50
        assert "calculated_cost" in data
        assert "budget_remaining" in data
        assert "is_over_budget" in data

class TestScenarioEdgeCases:
    """シナリオエッジケースのテストクラス"""
    
    @patch('routers.helpers.service.scenario_service.table')
    def test_empty_scenarios_list(self, mock_table):
        """空のシナリオリストのテスト"""
        mock_table.scan.return_value = {"Items": []}
        
        response = client.get("/scenarios")
        assert response.status_code == 200
        assert response.json() == []
    
    @patch('routers.helpers.service.scenario_service.table')
    def test_scenario_without_requests(self, mock_table):
        """リクエストデータなしのシナリオテスト"""
        mock_table.get_item.return_value = {
            "Item": {
                "scenario_id": "test-001",
                "name": "テストシナリオ",
                "end_month": 12,
                "current_month": 0,
                "features": []
            }
        }
        
        mock_table.query.return_value = {"Items": []}
        
        response = client.get("/scenarios/test-001")
        assert response.status_code == 200
        
        data = response.json()
        assert data["requests"] == []
    
    @patch('routers.helpers.service.scenario_service.table')
    def test_missing_feature_in_cost_calculation(self, mock_table):
        """コスト計算時にフィーチャーが見つからない場合のテスト"""
        # 月データは存在するが、フィーチャーが見つからない
        mock_table.get_item.side_effect = [
            {
                "Item": {
                    "scenario_id": "test-001",
                    "month": 0,
                    "feature": [{"feature_id": "missing-feature", "request": 1000}],
                    "funds": 50,
                    "description": "テスト"
                }
            },
            {"Item": None}  # フィーチャーが見つからない
        ]
        
        mock_table.query.return_value = {
            "Items": [{"costs": {"compute": {"cost": "10.00", "type": "per_month"}}}]
        }
        
        response = client.get("/scenarios/test-001/calculate-cost/0")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_requests"] == 0  # 見つからないフィーチャーはスキップ
        assert data["features_used"] == []

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
