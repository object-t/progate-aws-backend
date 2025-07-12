import pytest
import json
from unittest.mock import patch
from routers.costs import calculate_final_cost, find_resource_types
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestCostIntegration:
    """実際のシナリオデータを使った統合テスト"""

    def load_scenario_data(self):
        """シナリオデータを読み込む"""
        try:
            with open(
                "/Users/kanaha/Documents/GitHub/progate-aws-backend/personal_blog_scenario.json",
                "r",
                encoding="utf-8",
            ) as f:
                return json.load(f)
        except FileNotFoundError:
            pytest.skip("シナリオファイルが見つかりません")

    def test_personal_blog_scenario_structure(self):
        """個人ブログシナリオの構造テスト"""
        scenario_data = self.load_scenario_data()

        # 基本的な構造の確認
        assert "scenario_id" in scenario_data
        assert "name" in scenario_data
        assert "features" in scenario_data
        assert scenario_data["name"] == "個人ブログ"

    def test_extract_resources_from_scenario(self):
        """シナリオからリソースタイプを抽出するテスト"""
        scenario_data = self.load_scenario_data()

        # featuresからリソースタイプを抽出
        resource_types = []
        for feature in scenario_data.get("features", []):
            if "type" in feature:
                resource_types.append(feature["type"])

        # 期待されるリソースタイプが含まれているか確認
        expected_types = ["compute", "domain", "database"]
        for expected_type in expected_types:
            assert expected_type in resource_types

    @patch("routers.costs.table")
    def test_calculate_blog_scenario_cost(self, mock_table):
        """個人ブログシナリオのコスト計算テスト"""
        # モックのコストデータ
        mock_costs = {
            "compute": {"cost": "8.50", "type": "per_month"},
            "domain": {"cost": "12.00", "type": "per_month"},
            "database": {"cost": "15.00", "type": "per_month"},
            "storage": {"cost": "0.023", "type": "per_request"},
        }

        mock_table.query.return_value = {"Items": [{"costs": mock_costs}]}

        # シナリオデータを構造データに変換
        scenario_data = self.load_scenario_data()
        struct_data = {}

        for feature in scenario_data.get("features", []):
            if "type" in feature:
                struct_data[feature["id"]] = {"type": feature["type"]}

        request_data = {"struct_data": struct_data, "num_requests": 5000}

        response = client.post("/calculate", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert "final_cost" in data
        assert "breakdown" in data

        # 月額固定費の確認（compute + domain + database）
        expected_monthly = 8.50 + 12.00 + 15.00  # 35.50
        assert data["breakdown"]["monthly_cost"] == expected_monthly

    def test_realistic_blog_traffic_scenarios(self):
        """現実的なブログトラフィックシナリオのテスト"""
        struct_data = {
            "web_server": {"type": "ec2"},
            "database": {"type": "rds"},
            "cdn": {"type": "cloudfront"},
        }

        costs_db = {
            "ec2": {"cost": "8.50", "type": "per_month"},
            "rds": {"cost": "15.00", "type": "per_month"},
            "cloudfront": {"cost": "0.0001", "type": "per_request"},
        }

        # 低トラフィック（月1000リクエスト）
        low_traffic_cost = calculate_final_cost(struct_data, costs_db, 1000)
        expected_low = 23.50 + (0.0001 * 1000)  # 23.60
        assert low_traffic_cost == expected_low

        # 中トラフィック（月10000リクエスト）
        medium_traffic_cost = calculate_final_cost(struct_data, costs_db, 10000)
        expected_medium = 23.50 + (0.0001 * 10000)  # 24.50
        assert medium_traffic_cost == expected_medium

        # 高トラフィック（月100000リクエスト）
        high_traffic_cost = calculate_final_cost(struct_data, costs_db, 100000)
        expected_high = 23.50 + (0.0001 * 100000)  # 33.50
        assert high_traffic_cost == expected_high

    def test_complex_nested_structure(self):
        """複雑なネスト構造のテスト"""
        complex_struct = {
            "infrastructure": {
                "compute": {
                    "web_tier": [
                        {"type": "ec2", "name": "web1"},
                        {"type": "ec2", "name": "web2"},
                    ],
                    "app_tier": {"type": "lambda", "name": "api"},
                },
                "data": {
                    "primary_db": {"type": "rds", "engine": "mysql"},
                    "cache": {"type": "elasticache", "engine": "redis"},
                },
            },
            "networking": {"vpc": {"type": "vpc"}, "load_balancer": {"type": "alb"}},
        }

        resource_types = list(find_resource_types(complex_struct))

        # 期待されるリソースタイプ
        expected_types = ["ec2", "lambda", "rds", "elasticache", "vpc", "alb"]
        for expected_type in expected_types:
            assert expected_type in resource_types

        # ec2が2回出現することを確認
        assert resource_types.count("ec2") == 2

    @patch("routers.costs.table")
    def test_cost_breakdown_accuracy(self, mock_table):
        """コスト内訳の正確性テスト"""
        mock_costs = {
            "ec2": {"cost": "10.00", "type": "per_month"},
            "lambda": {"cost": "0.0002", "type": "per_request"},
            "rds": {"cost": "25.00", "type": "per_month"},
        }

        mock_table.query.return_value = {"Items": [{"costs": mock_costs}]}

        struct_data = {
            "web": {"type": "ec2"},
            "api": {"type": "lambda"},
            "db": {"type": "rds"},
        }

        request_data = {"struct_data": struct_data, "num_requests": 15000}

        response = client.post("/calculate", json=request_data)
        data = response.json()

        # 内訳の確認
        assert data["breakdown"]["monthly_cost"] == 35.00  # 10 + 25
        assert data["breakdown"]["request_cost"] == 3.00  # 0.0002 * 15000
        assert data["final_cost"] == 38.00  # 35 + 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
