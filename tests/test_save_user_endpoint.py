import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from moto import mock_aws
import boto3
import os
from main import app
from routers.extractor import extract_user_id_from_token


@pytest.fixture
def client():
    # dependency_overridesを使用して認証をモック
    def mock_extract_user_id():
        return "test-user-id-123"
    
    app.dependency_overrides[extract_user_id_from_token] = mock_extract_user_id
    
    yield TestClient(app)
    
    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()


@pytest.fixture
def mock_user_id():
    """テスト用のユーザーID"""
    return "test-user-id-123"


@pytest.fixture
def mock_dynamodb_setup():
    """DynamoDBのモック環境をセットアップ"""
    # 環境変数を設定
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    
    with mock_aws():
        # DynamoDBリソースを作成
        dynamodb = boto3.resource(
            "dynamodb",
            region_name="us-east-1",
            aws_access_key_id="testing",
            aws_secret_access_key="testing",
        )
        
        # テーブルを作成
        table = dynamodb.create_table(
            TableName="users",
            KeySchema=[
                {"AttributeName": "UserId", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "UserId", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        
        # テーブルが作成されるまで待機
        table.wait_until_exists()
        
        # settings.pyの設定をモック
        with patch("routers.user.settings") as mock_settings:
            mock_settings.DYNAMODB_ENDPOINT = None
            mock_settings.REGION = "us-east-1"
            mock_settings.AWS_ACCESS_KEY_ID = "testing"
            mock_settings.AWS_SECRET_ACCESS_KEY = "testing"
            
            # DynamoDBリソースもモック
            with patch("routers.user.dynamodb", dynamodb):
                with patch("routers.user.table", table):
                    yield table


def test_save_user_success(client, mock_user_id, mock_dynamodb_setup):
    """save_userエンドポイントの正常系テスト"""
    table = mock_dynamodb_setup
    
    # リクエストデータ
    request_data = {"username": "testuser"}
    
    # APIコール
    response = client.post(
        "/api/user",
        json=request_data,
        headers={"Authorization": "Bearer dummy_token"}  # ダミートークン
    )
    
    # デバッグ用
    if response.status_code != 200:
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    
    # レスポンスを確認
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["message"] == "ユーザー登録完了"
    assert response_data["user"]["username"] == "testuser"
    
    # DynamoDBにデータが保存されているか確認
    item = table.get_item(Key={"UserId": mock_user_id})
    assert "Item" in item
    assert item["Item"]["username"] == "testuser"
    assert item["Item"]["UserId"] == mock_user_id

def test_save_user_invalid_username(client, mock_user_id, mock_dynamodb_setup):
    """無効なユーザー名でのテスト"""
    
    # 空のユーザー名（現在のモデルでは空文字列も有効）
    request_data = {"username": ""}
    
    response = client.post(
        "/api/user",
        json=request_data,
        headers={"Authorization": "Bearer dummy_token"}
    )
    
    # 現在のモデルでは空文字列も有効なため、200が返されることを確認
    assert response.status_code == 200


def test_save_user_missing_username(client, mock_user_id, mock_dynamodb_setup):
    """ユーザー名フィールドが欠如しているテスト"""
    
    # usernameフィールドなし
    request_data = {}
    
    response = client.post(
        "/api/user",
        json=request_data,
        headers={"Authorization": "Bearer dummy_token"}
    )
    
    # バリデーションエラーが発生することを確認
    assert response.status_code == 422


def test_save_user_duplicate_user(client, mock_user_id, mock_dynamodb_setup):
    """同じユーザーIDで複数回登録するテスト"""
    table = mock_dynamodb_setup
    
    # 最初の登録
    request_data = {"username": "testuser1"}
    response1 = client.post(
        "/api/user",
        json=request_data,
        headers={"Authorization": "Bearer dummy_token"}
    )
    assert response1.status_code == 200
    
    # 同じユーザーIDで別のusernameで登録（上書きされる）
    request_data = {"username": "testuser2"}
    response2 = client.post(
        "/api/user",
        json=request_data,
        headers={"Authorization": "Bearer dummy_token"}
    )
    assert response2.status_code == 200
    
    # DynamoDBで最新のデータが保存されているか確認
    item = table.get_item(Key={"UserId": mock_user_id})
    assert "Item" in item
    assert item["Item"]["username"] == "testuser2"  # 上書きされている


if __name__ == "__main__":
    # テストを直接実行する場合
    import sys
    pytest.main([__file__, "-v"] + sys.argv[1:])
