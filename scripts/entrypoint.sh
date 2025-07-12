#!/bin/bash

# エントリーポイントスクリプト
# アプリケーション起動前にデータ初期化を実行

set -e

echo "🚀 アプリケーション起動準備中..."

# バックグラウンドでデータ初期化を実行
# アプリケーションの起動を遅らせないように非同期で実行
if [ "${INIT_DATA:-true}" = "true" ]; then
    echo "📦 データ初期化をバックグラウンドで開始..."
    /app/scripts/init-data.sh &
    INIT_PID=$!
    
    # 初期化の完了を待つ（最大60秒）
    echo "⏳ データ初期化の完了を待機中..."
    timeout=60
    elapsed=0
    
    while kill -0 $INIT_PID 2>/dev/null && [ $elapsed -lt $timeout ]; do
        sleep 1
        elapsed=$((elapsed + 1))
        if [ $((elapsed % 10)) -eq 0 ]; then
            echo "⏳ データ初期化中... (${elapsed}s)"
        fi
    done
    
    if kill -0 $INIT_PID 2>/dev/null; then
        echo "⚠️  データ初期化がタイムアウトしました。バックグラウンドで継続実行中..."
    else
        wait $INIT_PID
        if [ $? -eq 0 ]; then
            echo "✅ データ初期化が完了しました"
        else
            echo "⚠️  データ初期化でエラーが発生しましたが、アプリケーションを起動します"
        fi
    fi
else
    echo "⏭️  データ初期化をスキップします (INIT_DATA=false)"
fi

echo "🚀 アプリケーションを起動します..."

# 元のコマンドを実行
exec "$@"
