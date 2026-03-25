$ErrorActionPreference = "Stop"

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
}

docker compose -f infra/compose/docker-compose.dev.yml --env-file .env up --build -d
