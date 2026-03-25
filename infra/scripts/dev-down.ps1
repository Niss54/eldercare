$ErrorActionPreference = "Stop"

docker compose -f infra/compose/docker-compose.dev.yml --env-file .env down
