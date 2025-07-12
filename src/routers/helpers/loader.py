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
from boto3.dynamodb.conditions import Key

# 親ディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from settings import get_DynamoDbSettings

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
        settings = get_DynamoDbSettings()
        return boto3.resource(
            "dynamodb",
            region_name=settings.REGION,
        )
    except Exception:
        # 設定ファイルが使えない場合はデフォルト値を使用
        return boto3.resource(
            "dynamodb",
            endpoint_url="http://dynamodb-local:8000",  # コンテナ内用
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
        # シナリオデータを格納（requestsも含む）
        main_item = {
            'PK': 'scenario',
            'SK': scenario_id,
            'scenario_id': scenario_id,
            'name': scenario_data.get('name', ''),
            'end_month': convert_to_dynamodb_format(scenario_data.get('end_month', 0)),
            'current_month': convert_to_dynamodb_format(scenario_data.get('current_month', 0)),
            'features': convert_to_dynamodb_format(scenario_data.get('features', [])),
            'requests': convert_to_dynamodb_format(scenario_data.get('requests', [])),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        table.put_item(Item=main_item)
        print(f"✅ シナリオデータを格納しました")
        
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
        # シナリオデータを検索
        response = table.query(
            KeyConditionExpression=Key("PK").eq("scenario")
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
            print(f"リクエスト数: {len(scenario.get('requests', []))}")
            print(f"作成日時: {scenario.get('created_at', 'N/A')}")
            print("-" * 40)
            
    except Exception as e:
        print(f"❌ エラー: DynamoDBからの読み込みに失敗しました: {e}")

def delete_scenario_from_dynamodb(scenario_id):
    """指定されたシナリオをDynamoDBから削除"""
    
    dynamodb = get_dynamodb_connection()
    table = dynamodb.Table("game")
    
    try:
        # シナリオアイテムを削除
        table.delete_item(
            Key={
                'PK': 'scenario',
                'SK': scenario_id
            }
        )
        
        print(f"✅ シナリオ '{scenario_id}' を削除しました")
        return True
        
    except Exception as e:
        print(f"❌ エラー: シナリオの削除に失敗しました: {e}")
        return False

def load_costs_to_dynamodb(costs_file_path: str) -> bool:
    """コストJSONファイルをDynamoDBに読み込み"""
    dynamodb = get_dynamodb_connection()
    table = dynamodb.Table("game")
    
    # コストファイルを読み込み
    try:
        with open(costs_file_path, 'r', encoding='utf-8') as f:
            costs_data = json.load(f)
    except FileNotFoundError:
        print(f"エラー: ファイル '{costs_file_path}' が見つかりません")
        return False
    except json.JSONDecodeError as e:
        print(f"エラー: JSONファイルの解析に失敗しました: {e}")
        return False
    
    print("コストデータを読み込み中...")
    
    try:
        # コストデータを格納
        costs_item = {
            'PK': 'costs',
            'SK': 'metadata',
            'costs': convert_to_dynamodb_format(costs_data.get('costs', {})),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        table.put_item(Item=costs_item)
        print(f"✅ コストデータを格納しました")
        
        print(f"\n🎉 コストデータの読み込みが完了しました！")
        
        # 現在のシナリオ一覧も表示
        list_scenarios_in_dynamodb()
        return True
        
    except Exception as e:
        print(f"❌ エラー: コストデータの格納に失敗しました: {e}")
        return False


def list_costs_in_dynamodb():
    """DynamoDB内のコストデータを表示"""
    dynamodb = get_dynamodb_connection()
    table = dynamodb.Table("game")
    
    try:
        # コストデータを取得
        response = table.get_item(
            Key={
                'PK': 'costs',
                'SK': 'metadata'
            }
        )
        
        item = response.get('Item')
        if not item:
            print("📭 DynamoDBにコストデータが見つかりません")
            return
        
        costs = item.get('costs', {})
        print(f"\n💰 DynamoDB内のコストデータ:")
        print("-" * 80)
        print(f"作成日時: {item.get('created_at', 'N/A')}")
        print(f"更新日時: {item.get('updated_at', 'N/A')}")
        print(f"コスト項目数: {len(costs)}件")
        print("-" * 40)
        
        # コスト項目を表示
        for service, cost_info in costs.items():
            cost_type = cost_info.get('type', 'unknown')
            cost_value = cost_info.get('cost', 0)
            print(f"{service}: ${cost_value} ({cost_type})")
        
        print("-" * 40)
            
    except Exception as e:
        print(f"❌ エラー: DynamoDBからの読み込みに失敗しました: {e}")


def delete_costs_from_dynamodb() -> bool:
    """DynamoDBからコストデータを削除"""
    dynamodb = get_dynamodb_connection()
    table = dynamodb.Table("game")
    
    try:
        # コストデータを削除
        table.delete_item(
            Key={
                'PK': 'costs',
                'SK': 'metadata'
            }
        )
        
        print("✅ コストデータを削除しました")
        return True
        
    except Exception as e:
        print(f"❌ エラー: コストデータの削除に失敗しました: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='シナリオJSONファイルをDynamoDBに格納')
    parser.add_argument('--load', type=str, help='読み込むシナリオJSONファイルのパス')
    parser.add_argument('--load-costs', type=str, help='読み込むコストJSONファイルのパス')
    parser.add_argument('--list', action='store_true', help='DynamoDB内のシナリオ一覧を表示')
    parser.add_argument('--list-costs', action='store_true', help='DynamoDB内のコストデータを表示')
    parser.add_argument('--delete', type=str, help='削除するシナリオID')
    parser.add_argument('--delete-costs', action='store_true', help='コストデータを削除')
    
    args = parser.parse_args()
    
    if args.load:
        success = load_scenario_to_dynamodb(args.load)
        if success:
            print("\n📋 現在のシナリオ一覧:")
            list_scenarios_in_dynamodb()
    elif args.load_costs:
        success = load_costs_to_dynamodb(args.load_costs)
        if success:
            print("✅ コストデータの読み込みが完了しました")
    elif args.list:
        list_scenarios_in_dynamodb()
    elif args.list_costs:
        list_costs_in_dynamodb()
    elif args.delete:
        success = delete_scenario_from_dynamodb(args.delete)
        if success:
            print("\n📋 残りのシナリオ一覧:")
            list_scenarios_in_dynamodb()
    elif args.delete_costs:
        success = delete_costs_from_dynamodb()
        if success:
            print("✅ コストデータの削除が完了しました")
    else:
        print("使用方法:")
        print("  シナリオを読み込む: python loader.py --load scenarios/personal_blog_scenario.json")
        print("  コストを読み込む: python loader.py --load-costs costs/dynamodb_costs.json")
        print("  シナリオ一覧表示: python loader.py --list")
        print("  コスト一覧表示: python loader.py --list-costs")
        print("  シナリオを削除: python loader.py --delete scenario-id")
        print("  コストを削除: python loader.py --delete-costs")

if __name__ == "__main__":
    main()
