import pytest
from unittest.mock import Mock, patch
from routers.costs import calculate_final_cost, find_resource_types
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

class TestCostCalculation:
    """コスト計算機能のテストクラス"""
    
    def test_find_resource_types_simple(self):
        """シンプルなリソースタイプ抽出のテスト"""
        struct_data = {
            "type": "ec2",
            "name": "web-server"
        }
        resource_types = list(find_resource_types(struct_data))
        assert "ec2" in resource_types
    
    def test_find_resource_types_nested(self):
        """ネストされた構造からのリソースタイプ抽出のテスト"""
        struct_data = {
            "vpc": {
                "type": "vpc",
                "subnets": [
                    {"type": "subnet", "name": "public"},
                    {"type": "subnet", "name": "private"}
                ]
            },
            "instances": {
                "web": {"type": "ec2", "instance_type": "t3.micro"},
                "db": {"type": "rds", "engine": "mysql"}
            }
        }
        resource_types = list(find_resource_types(struct_data))
        expected_types = ["vpc", "subnet", "ec2", "rds"]
        
        for expected_type in expected_types:
            assert expected_type in resource_types
        
        # subnetが2回出現することを確認
        assert resource_types.count("subnet") == 2
    
    def test_calculate_final_cost_monthly_only(self):
        """月額固定費のみのコスト計算テスト"""
        struct_data = {"type": "ec2"}
        costs_db = {
            "ec2": {"cost": "10.50", "type": "per_month"}
        }
        num_requests = 1000
        
        result = calculate_final_cost(struct_data, costs_db, num_requests)
        assert result == 10.50
    
    def test_calculate_final_cost_request_only(self):
        """リクエスト変動費のみのコスト計算テスト"""
        struct_data = {"type": "lambda"}
        costs_db = {
            "lambda": {"cost": "0.0001", "type": "per_request"}
        }
        num_requests = 10000
        
        result = calculate_final_cost(struct_data, costs_db, num_requests)
        assert result == 1.0  # 0.0001 * 10000
    
    def test_calculate_final_cost_mixed(self):
        """月額固定費とリクエスト変動費の混合テスト"""
        struct_data = {
            "web": {"type": "ec2"},
            "api": {"type": "lambda"}
        }
        costs_db = {
            "ec2": {"cost": "20.00", "type": "per_month"},
            "lambda": {"cost": "0.0002", "type": "per_request"}
        }
        num_requests = 5000
        
        result = calculate_final_cost(struct_data, costs_db, num_requests)
        expected = 20.00 + (0.0002 * 5000)  # 20.00 + 1.00 = 21.00
        assert result == expected
    
    def test_calculate_final_cost_unknown_resource(self):
        """未知のリソースタイプのテスト"""
        struct_data = {"type": "unknown_service"}
        costs_db = {
            "ec2": {"cost": "10.00", "type": "per_month"}
        }
        num_requests = 1000
        
        result = calculate_final_cost(struct_data, costs_db, num_requests)
        assert result == 0.0
    
    def test_calculate_final_cost_empty_struct(self):
        """空の構造データのテスト"""
        struct_data = {}
        costs_db = {
            "ec2": {"cost": "10.00", "type": "per_month"}
        }
        num_requests = 1000
        
        result = calculate_final_cost(struct_data, costs_db, num_requests)
        assert result == 0.0

class TestCostAPI:
    """コスト計算APIのテストクラス"""
    
    @patch('routers.costs.table')
    def test_get_costs_success(self, mock_table):
        """コスト情報取得APIの成功テスト"""
        mock_table.query.return_value = {
            "Items": [{
                "costs": {
                    "ec2": {"cost": "10.00", "type": "per_month"},
                    "lambda": {"cost": "0.0001", "type": "per_request"}
                }
            }]
        }
        
        response = client.get("/costs")
        assert response.status_code == 200
        data = response.json()
        assert "ec2" in data
        assert "lambda" in data
    
    @patch('routers.costs.table')
    def test_calculate_cost_success(self, mock_table):
        """コスト計算APIの成功テスト"""
        mock_table.query.return_value = {
            "Items": [{
                "costs": {
                    "ec2": {"cost": "15.00", "type": "per_month"},
                    "lambda": {"cost": "0.0002", "type": "per_request"}
                }
            }]
        }
        
        request_data = {
            "struct_data": {
                "web": {"type": "ec2"},
                "api": {"type": "lambda"}
            },
            "num_requests": 2000
        }
        
        response = client.post("/calculate", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "final_cost" in data
        assert "resource_types" in data
        assert "breakdown" in data
        
        # 期待値: 15.00 (月額) + 0.0002 * 2000 (リクエスト) = 15.40
        assert data["final_cost"] == 15.40
        assert data["num_requests"] == 2000
        assert "ec2" in data["resource_types"]
        assert "lambda" in data["resource_types"]
    
    @patch('routers.costs.table')
    def test_calculate_cost_no_data(self, mock_table):
        """コストデータが見つからない場合のテスト"""
        mock_table.query.return_value = {"Items": []}
        
        request_data = {
            "struct_data": {"type": "ec2"},
            "num_requests": 1000
        }
        
        response = client.post("/calculate", json=request_data)
        assert response.status_code == 404
        assert "Cost data not found" in response.json()["detail"]

class TestEdgeCases:
    """エッジケースのテストクラス"""
    
    def test_find_resource_types_with_none_values(self):
        """None値を含む構造のテスト"""
        struct_data = {
            "type": "ec2",
            "config": None,
            "nested": {
                "type": "rds",
                "value": None
            }
        }
        resource_types = list(find_resource_types(struct_data))
        assert "ec2" in resource_types
        assert "rds" in resource_types
    
    def test_calculate_final_cost_with_zero_requests(self):
        """リクエスト数が0の場合のテスト"""
        struct_data = {"type": "lambda"}
        costs_db = {
            "lambda": {"cost": "0.0001", "type": "per_request"}
        }
        num_requests = 0
        
        result = calculate_final_cost(struct_data, costs_db, num_requests)
        assert result == 0.0
    
    def test_calculate_final_cost_with_string_costs(self):
        """コストが文字列の場合のテスト"""
        struct_data = {"type": "ec2"}
        costs_db = {
            "ec2": {"cost": "25.99", "type": "per_month"}
        }
        num_requests = 1000
        
        result = calculate_final_cost(struct_data, costs_db, num_requests)
        assert result == 25.99

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
