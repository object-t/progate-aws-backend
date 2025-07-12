#!/bin/bash

# データ初期化スクリプト
# コンテナ起動時に最低限必要なデータを読み込む

set -e

echo "🚀 データ初期化を開始します..."

# DynamoDBの接続を待機
echo "⏳ DynamoDBの起動を待機中..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if python -c "
import sys
import os
sys.path.append('/app/src')
try:
    from settings import get_DynamoDbConnect
    import boto3
    
    db_config = get_DynamoDbConnect()
    dynamodb = boto3.client(
        'dynamodb',
        endpoint_url=db_config.DYNAMODB_ENDPOINT,
        aws_access_key_id=db_config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=db_config.AWS_SECRET_ACCESS_KEY,
        region_name=db_config.REGION
    )
    
    # DynamoDBサービスの接続確認
    dynamodb.list_tables()
    print('DynamoDB接続成功')
    exit(0)
except Exception as e:
    print(f'DynamoDB接続失敗: {e}')
    exit(1)
" 2>/dev/null; then
        echo "✅ DynamoDBに接続しました"
        break
    fi
    
    attempt=$((attempt + 1))
    echo "🔄 DynamoDB接続試行 $attempt/$max_attempts"
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ DynamoDBへの接続がタイムアウトしました"
    exit 1
fi

# テーブルを作成
echo "📋 DynamoDBテーブルを作成中..."
python /app/scripts/create-table.py

# データが既に存在するかチェック
echo "📋 既存データをチェック中..."
data_exists=$(python -c "
import sys
import os
sys.path.append('/app/src')
try:
    from routers.helpers.service import scenario_service
    import asyncio
    
    async def check_data():
        try:
            scenarios = await scenario_service.get_all_scenarios()
            return len(scenarios) > 0
        except:
            return False
    
    result = asyncio.run(check_data())
    print('true' if result else 'false')
except Exception as e:
    print('false')
" 2>/dev/null)

if [ "$data_exists" = "false" ]; then
    echo "📦 初期データを読み込み中..."
    
    # 個人ブログシナリオを読み込み
    if [ -f "/app/src/routers/helpers/scenarios/personal_blog_scenario.json" ]; then
        echo "📖 個人ブログシナリオを読み込み中..."
        cd /app/src/routers/helpers
        python loader.py --load scenarios/personal_blog_scenario.json
    else
        echo "⚠️  個人ブログシナリオファイルが見つかりません"
    fi
    
    # 企業サイトシナリオを読み込み
    if [ -f "/app/src/routers/helpers/scenarios/corporate_site_scenario.json" ]; then
        echo "📖 企業サイトシナリオを読み込み中..."
        cd /app/src/routers/helpers
        python loader.py --load scenarios/corporate_site_scenario.json
    else
        echo "⚠️  企業サイトシナリオファイルが見つかりません"
    fi
    
    # コストデータを読み込み
    if [ -f "/app/src/routers/helpers/costs/dynamodb_costs.json" ]; then
        echo "💰 コストデータを読み込み中..."
        cd /app/src/routers/helpers
        python loader.py --load-costs costs/dynamodb_costs.json
    else
        echo "⚠️  コストデータファイルが見つかりません"
    fi
    
    echo "🎉 初期データの読み込みが完了しました！"
else
    echo "✅ 既存データが見つかりました。初期化をスキップします。"
fi

echo "🏁 データ初期化が完了しました"
