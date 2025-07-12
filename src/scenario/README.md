# シナリオ管理モジュール

## 概要
シナリオJSONファイルをDynamoDBに格納し、APIを通じてシナリオデータの管理とコスト計算を行うモジュールです。

## ディレクトリ構造
```
src/
├── models/
│   └── scenario.py             # シナリオ関連のPydanticモデル
├── routers/
│   └── scenarios.py            # シナリオ関連のAPIルーター
└── scenario/
    ├── __init__.py             # モジュール初期化
    ├── README.md              # このファイル
    ├── service.py             # ビジネスロジック層
    ├── loader.py              # データ読み込みスクリプト
    ├── tests.py               # テストファイル
    ├── personal_blog_scenario.json
    └── corporate_site_scenario.json
```

## 機能一覧

### 1. データモデル (`src/models/scenario.py`)
- `Scenario`: シナリオの完全なデータモデル
- `ScenarioSummary`: シナリオ一覧用の要約モデル
- `Feature`: フィーチャーモデル
- `MonthlyRequest`: 月別リクエストモデル
- `CostCalculationResult`: コスト計算結果モデル

### 2. サービス層 (`service.py`)
- `ScenarioService`: シナリオ管理の中核ビジネスロジック
- DynamoDB操作の抽象化
- エラーハンドリング
- データ変換処理

### 3. API層 (`src/routers/scenarios.py`)
- RESTful APIエンドポイント
- リクエスト/レスポンスの型安全性
- 自動ドキュメント生成対応

### 4. データローダー (`loader.py`)
- JSONファイルからDynamoDBへの一括読み込み
- シナリオ一覧表示
- シナリオ削除機能

## 使用方法

### データの読み込み
```bash
cd src/scenario

# シナリオを読み込み
uv run python loader.py --load personal_blog_scenario.json

# シナリオ一覧を表示
uv run python loader.py --list

# シナリオを削除
uv run python loader.py --delete scenario-id
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

## APIエンドポイント

| メソッド | エンドポイント | 説明 | レスポンスモデル |
|---------|---------------|------|-----------------|
| GET | `/scenarios` | シナリオ一覧取得 | `List[ScenarioSummary]` |
| GET | `/scenarios/{id}` | シナリオ詳細取得 | `Scenario` |
| GET | `/scenarios/{id}/month/{month}` | 月別データ取得 | `MonthData` |
| GET | `/features/{id}` | フィーチャー詳細取得 | `FeatureDetail` |
| GET | `/scenarios/{id}/calculate-cost/{month}` | コスト計算 | `CostCalculationResult` |

## テスト

```bash
# シナリオモジュールのテストを実行
uv run pytest src/scenario/tests.py -v

# 全テストを実行
uv run pytest src/tests/ src/scenario/tests.py -v
```

## データ構造

### DynamoDBテーブル構造

#### シナリオメタデータ
```
PK: scenario#{scenario_id}
SK: metadata
Data: {
  scenario_id: string,
  name: string,
  end_month: number,
  current_month: number,
  features: Feature[],
  created_at: string,
  updated_at: string
}
```

#### 月別リクエストデータ
```
PK: scenario#{scenario_id}
SK: request#{month:03d}
Data: {
  scenario_id: string,
  month: number,
  feature: RequestFeature[],
  funds: number,
  description: string,
  created_at: string
}
```

#### フィーチャーデータ
```
PK: feature#{feature_id}
SK: metadata
Data: {
  feature_id: string,
  scenario_id: string,
  type: string,
  feature: string,
  required: string[],
  created_at: string
}
```

## 設計原則

### 1. 関心の分離
- **Models**: データ構造の定義
- **Service**: ビジネスロジック
- **Routes**: HTTP API層
- **Loader**: データ操作ツール

### 2. 型安全性
- Pydanticモデルによる型チェック
- FastAPIの自動バリデーション
- TypeHintの活用

### 3. テスタビリティ
- 依存性注入パターン
- モック可能な設計
- 単体テストと統合テストの分離

### 4. エラーハンドリング
- 適切なHTTPステータスコード
- 詳細なエラーメッセージ
- ログ出力

## 拡張性

### 新しいフィーチャータイプの追加
1. `models.py`でモデルを拡張
2. `service.py`でビジネスロジックを追加
3. `tests.py`でテストケースを追加

### 新しいAPIエンドポイントの追加
1. `routes.py`にエンドポイントを追加
2. 必要に応じて`service.py`にメソッドを追加
3. `tests.py`でテストを追加

## トラブルシューティング

### DynamoDB接続エラー
```bash
# Docker Composeが起動しているか確認
docker compose ps

# DynamoDBが応答するか確認
curl http://localhost:8000
```

### インポートエラー
```bash
# Pythonパスを確認
cd src/scenario
python -c "import sys; print(sys.path)"

# 親ディレクトリから実行
cd src
python -m scenario.loader --list
```

### テストエラー
```bash
# 依存関係を確認
uv sync

# テストを個別実行
uv run pytest src/scenario/tests.py::TestScenariosAPI::test_get_scenarios_success -v
```
