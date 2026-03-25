$ErrorActionPreference = "Stop"

$api = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing
$web = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing

if ($api.StatusCode -ne 200) {
  throw "API health check failed"
}
if ($web.StatusCode -ne 200) {
  throw "Web health check failed"
}

docker compose -f infra/compose/docker-compose.dev.yml --env-file .env ps
Write-Host "Core service health checks passed." -ForegroundColor Green
