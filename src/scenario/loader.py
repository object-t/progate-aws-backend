#!/usr/bin/env python3
"""
シナリオJSONファイルをDynamoDBに格納するスクリプト
"""
import json
import boto3
import uuid
from decimal import Decimal
from pathlib import Path
import argparse
from datetime import datetime
import sys
import os

# 親ディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from settings import get_DynamoDbConnect

def convert_to_dynamodb_format(obj):
    """PythonオブジェクトをDynamoDB形式に変換"""
    if isinstance(obj, dict):
        return {k: convert_to_dynamodb_format(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_dynamodb_format(item) for item in obj]
    elif isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, int):
        return Decimal(str(obj))
    else:
        return obj

def get_dynamodb_connection():
    """DynamoDB接続を取得"""
    try:
        settings = get_DynamoDbConnect()
        # Docker環境外からアクセスする場合はlocalhostに変更
        endpoint_url = settings.DYNAMODB_ENDPOINT.replace('dynamodb-local', 'localhost')
        return boto3.resource(
            "dynamodb",
            region_name=settings.REGION,
        )
    except Exception:
        # 設定ファイルが使えない場合はデフォルト値を使用
        return boto3.resource(
            "dynamodb",
            endpoint_url="http://localhost:8000",
            region_name="ap-northeast-1",
            aws_access_key_id="local",
            aws_secret_access_key="local",
        )

def load_scenario_to_dynamodb(scenario_file_path):
    """シナリオファイルをDynamoDBに読み込む"""
    
    # DynamoDB接続設定
    dynamodb = get_dynamodb_connection()
    table = dynamodb.Table("game")
    
    # シナリオファイルを読み込み
    try:
        with open(scenario_file_path, 'r', encoding='utf-8') as f:
            scenario_data = json.load(f)
    except FileNotFoundError:
        print(f"エラー: ファイル '{scenario_file_path}' が見つかりません")
        return False
    except json.JSONDecodeError as e:
        print(f"エラー: JSONファイルの解析に失敗しました: {e}")
        return False
    
    scenario_id = scenario_data.get('scenario_id', str(uuid.uuid4()))
    
    print(f"シナリオ '{scenario_data.get('name', 'Unknown')}' (ID: {scenario_id}) を読み込み中...")
    
    try:
        # メインシナリオデータを格納
        main_item = {
            'PK': f'scenario#{scenario_id}',
            'SK': 'metadata',
            'scenario_id': scenario_id,
            'name': scenario_data.get('name', ''),
            'end_month': convert_to_dynamodb_format(scenario_data.get('end_month', 0)),
            'current_month': convert_to_dynamodb_format(scenario_data.get('current_month', 0)),
            'features': convert_to_dynamodb_format(scenario_data.get('features', [])),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        table.put_item(Item=main_item)
        print(f"✅ メインシナリオデータを格納しました")
        
        # リクエストデータを個別に格納
        requests = scenario_data.get('requests', [])
        for request_data in requests:
            month = request_data.get('month', 0)
            request_item = {
                'PK': f'scenario#{scenario_id}',
                'SK': f'request#{month:03d}',
                'scenario_id': scenario_id,
                'month': convert_to_dynamodb_format(month),
                'feature': convert_to_dynamodb_format(request_data.get('feature', [])),
                'funds': convert_to_dynamodb_format(request_data.get('funds', 0)),
                'description': request_data.get('description', ''),
                'created_at': datetime.now().isoformat()
            }
            
            table.put_item(Item=request_item)
            print(f"✅ 月 {month} のリクエストデータを格納しました")
        
        # フィーチャーデータを個別に格納（検索用）
        features = scenario_data.get('features', [])
        for feature in features:
            feature_id = feature.get('id', str(uuid.uuid4()))
            feature_item = {
                'PK': f'feature#{feature_id}',
                'SK': 'metadata',
                'scenario_id': scenario_id,
                'feature_id': feature_id,
                'type': feature.get('type', ''),
                'feature': feature.get('feature', ''),
                'required': convert_to_dynamodb_format(feature.get('required', [])),
                'created_at': datetime.now().isoformat()
            }
            
            table.put_item(Item=feature_item)
            print(f"✅ フィーチャー '{feature.get('feature', 'Unknown')}' を格納しました")
        
        print(f"\n🎉 シナリオ '{scenario_data.get('name')}' の読み込みが完了しました！")
        return True
        
    except Exception as e:
        print(f"❌ エラー: DynamoDBへの書き込みに失敗しました: {e}")
        return False

def list_scenarios_in_dynamodb():
    """DynamoDB内のシナリオ一覧を表示"""
    
    dynamodb = get_dynamodb_connection()
    table = dynamodb.Table("game")
    
    try:
        # シナリオメタデータを検索
        response = table.scan(
            FilterExpression="begins_with(PK, :pk) AND SK = :sk",
            ExpressionAttributeValues={
                ':pk': 'scenario#',
                ':sk': 'metadata'
            }
        )
        
        scenarios = response.get('Items', [])
        
        if not scenarios:
            print("📭 DynamoDBにシナリオが見つかりません")
            return
        
        print(f"\n📋 DynamoDB内のシナリオ一覧 ({len(scenarios)}件):")
        print("-" * 80)
        
        for scenario in scenarios:
            print(f"ID: {scenario.get('scenario_id', 'N/A')}")
            print(f"名前: {scenario.get('name', 'N/A')}")
            print(f"期間: {scenario.get('end_month', 'N/A')}ヶ月")
            print(f"フィーチャー数: {len(scenario.get('features', []))}")
            print(f"作成日時: {scenario.get('created_at', 'N/A')}")
            print("-" * 40)
            
    except Exception as e:
        print(f"❌ エラー: DynamoDBからの読み込みに失敗しました: {e}")

def delete_scenario_from_dynamodb(scenario_id):
    """指定されたシナリオをDynamoDBから削除"""
    
    dynamodb = get_dynamodb_connection()
    table = dynamodb.Table("game")
    
    try:
        # シナリオ関連のアイテムを検索
        response = table.query(
            KeyConditionExpression="PK = :pk",
            ExpressionAttributeValues={
                ':pk': f'scenario#{scenario_id}'
            }
        )
        
        items = response.get('Items', [])
        
        if not items:
            print(f"⚠️  シナリオ ID '{scenario_id}' が見つかりません")
            return False
        
        # 関連するフィーチャーも削除
        feature_response = table.scan(
            FilterExpression="scenario_id = :sid",
            ExpressionAttributeValues={
                ':sid': scenario_id
            }
        )
        
        feature_items = feature_response.get('Items', [])
        
        # 削除実行
        deleted_count = 0
        
        # シナリオアイテムを削除
        for item in items:
            table.delete_item(
                Key={
                    'PK': item['PK'],
                    'SK': item['SK']
                }
            )
            deleted_count += 1
        
        # フィーチャーアイテムを削除
        for item in feature_items:
            if item['PK'].startswith('feature#'):
                table.delete_item(
                    Key={
                        'PK': item['PK'],
                        'SK': item['SK']
                    }
                )
                deleted_count += 1
        
        print(f"✅ シナリオ '{scenario_id}' を削除しました ({deleted_count}件のアイテム)")
        return True
        
    except Exception as e:
        print(f"❌ エラー: シナリオの削除に失敗しました: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='シナリオJSONファイルをDynamoDBに格納')
    parser.add_argument('--load', type=str, help='読み込むシナリオJSONファイルのパス')
    parser.add_argument('--list', action='store_true', help='DynamoDB内のシナリオ一覧を表示')
    parser.add_argument('--delete', type=str, help='削除するシナリオID')
    
    args = parser.parse_args()
    
    if args.load:
        success = load_scenario_to_dynamodb(args.load)
        if success:
            print("\n📋 現在のシナリオ一覧:")
            list_scenarios_in_dynamodb()
    elif args.list:
        list_scenarios_in_dynamodb()
    elif args.delete:
        success = delete_scenario_from_dynamodb(args.delete)
        if success:
            print("\n📋 残りのシナリオ一覧:")
            list_scenarios_in_dynamodb()
    else:
        print("使用方法:")
        print("  シナリオを読み込む: python loader.py --load personal_blog_scenario.json")
        print("  シナリオ一覧表示: python loader.py --list")
        print("  シナリオを削除: python loader.py --delete scenario-id")

if __name__ == "__main__":
    main()
