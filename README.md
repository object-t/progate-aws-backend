# Set up 
```zsh
uv sync
cp .env.example .env
```

# サーバー起動
Dynamo DBと繋げたり、DockerでFastAPI起動する場合は、

```zsh
docker compose up -d
```
で起動できます。

## FastAPI
http://localhost:8080

## DynamoDB
http://localhost:8000

## DynamoDB Admin 
ブラウザ上でDynamo DBいじれます。
http://localhost:8001




# ファイルの実行
```zsh
uv run main.py
```

# add library
本番環境で必要なものは、
```zsh
uv add ~~
```

開発環境でのみ必要なものは、
```zsh
uv add --dev ~~
```

で追加してください。

# Lint and Format
PR出す前などに、LintやFormat挟んでもらえると助かります。

## Lint 
```zsh
uvx ruff check .
```

## Format
```zsh
uvx ruff format .
```


