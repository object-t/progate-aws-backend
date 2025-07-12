# シナリオ管理ヘルパー

## 概要
シナリオJSONファイルをDynamoDBに格納し、APIを通じてシナリオデータの管理とコスト計算を行うヘルパー機能です。

## ディレクトリ構造
```
src/routers/helpers/
├── __init__.py             # モジュール初期化
├── README.md              # このファイル
├── service.py             # ビジネスロジック層
├── loader.py              # データ読み込みスクリプト
├── tests.py               # テストファイル
├── scenarios/             # シナリオJSONファイル
│   ├── personal_blog_scenario.json
│   └── corporate_site_scenario.json
└── costs/                 # コストJSONファイル
    └── dynamodb_costs.json
```

## 使用方法

### データの読み込み
```bash
cd src/routers/helpers

# 個人ブログシナリオを読み込み
uv run python loader.py --load scenarios/personal_blog_scenario.json

# 企業サイトシナリオを読み込み
uv run python loader.py --load scenarios/corporate_site_scenario.json

# コストデータを読み込み
uv run python loader.py --load-costs costs/dynamodb_costs.json

# シナリオ一覧を表示
uv run python loader.py --list

# コストデータを表示
uv run python loader.py --list-costs

# シナリオを削除
uv run python loader.py --delete scenario-id

# コストデータを削除
uv run python loader.py --delete-costs
```

### API使用例
```bash
# シナリオ一覧取得
curl "http://localhost:8080/scenarios"

# シナリオ詳細取得
curl "http://localhost:8080/scenarios/personal-blog-001"

# 月別データ取得
curl "http://localhost:8080/scenarios/personal-blog-001/month/0"

# フィーチャー詳細取得
curl "http://localhost:8080/features/blog-web-001"

# コスト計算
curl "http://localhost:8080/scenarios/personal-blog-001/calculate-cost/0"
```

## ファイル説明

### `loader.py`
- JSONファイルからDynamoDBへの一括読み込み
- シナリオ一覧表示
- シナリオ削除機能
- コストデータの読み込み・表示・削除機能

### `service.py`
- シナリオ管理のビジネスロジック
- DynamoDB操作の抽象化
- エラーハンドリング

### `scenarios/`
- `personal_blog_scenario.json`: 個人ブログの成長シナリオ（12ヶ月）
- `corporate_site_scenario.json`: 企業サイトの成長シナリオ（36ヶ月）

### `costs/`
- `dynamodb_costs.json`: AWSサービスのコスト情報（PK="costs", SK="metadata"）

## テスト

```bash
# ヘルパー機能のテストを実行
cd src/routers/helpers
uv run python -m pytest tests.py -v
```

## トラブルシューティング

### ファイルが見つからないエラー
```bash
# 現在のディレクトリを確認
pwd

# ファイルの存在を確認
ls -la scenarios/

# 正しいディレクトリから実行
cd src/routers/helpers
```

### DynamoDB接続エラー
```bash
# Docker Composeが起動しているか確認
docker compose ps

# DynamoDBが応答するか確認
curl http://localhost:8000
```
