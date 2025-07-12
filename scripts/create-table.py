#!/usr/bin/env python3
"""
DynamoDBテーブル作成スクリプト
"""

import sys
import os

sys.path.append("/app/src")

import boto3
from settings import get_DynamoDbConnect


def create_table():
    """DynamoDBテーブルを作成"""
    try:
        db_config = get_DynamoDbConnect()
        dynamodb = boto3.resource(
            "dynamodb",
            endpoint_url=db_config.DYNAMODB_ENDPOINT,
            aws_access_key_id=db_config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=db_config.AWS_SECRET_ACCESS_KEY,
            region_name=db_config.REGION,
        )

        # テーブルが既に存在するかチェック
        try:
            table = dynamodb.Table("game")
            table.load()
            print("✅ テーブル 'game' は既に存在します")
            return True
        except Exception:
            pass

        # テーブルを作成
        print("📋 テーブル 'game' を作成中...")
        table = dynamodb.create_table(
            TableName="game",
            KeySchema=[
                {
                    "AttributeName": "PK",
                    "KeyType": "HASH",  # Partition key
                },
                {
                    "AttributeName": "SK",
                    "KeyType": "RANGE",  # Sort key
                },
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # テーブルの作成完了を待機
        print("⏳ テーブル作成の完了を待機中...")
        table.wait_until_exists()

        print("✅ テーブル 'game' の作成が完了しました")
        return True

    except Exception as e:
        print(f"❌ テーブル作成エラー: {e}")
        return False


if __name__ == "__main__":
    success = create_table()
    sys.exit(0 if success else 1)
