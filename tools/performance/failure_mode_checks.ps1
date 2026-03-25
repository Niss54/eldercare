$ErrorActionPreference = "Stop"

Write-Host "Running failure-mode checks..." -ForegroundColor Cyan

$badLogin = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/auth/login" -Method Post -ContentType "application/json" -Body '{"username":"admin@example.com","password":"wrong"}' -SkipHttpErrorCheck
if ($badLogin.StatusCode -ne 401) {
  throw "Expected 401 for invalid login"
}

$missingToken = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/auth/me" -Method Get -SkipHttpErrorCheck
if ($missingToken.StatusCode -ne 401) {
  throw "Expected 401 for missing bearer token"
}

$health = Invoke-WebRequest -Uri "http://localhost:8000/health" -Method Get -SkipHttpErrorCheck
if ($health.StatusCode -ne 200) {
  throw "Health endpoint did not return 200"
}

Write-Host "Failure-mode checks completed successfully." -ForegroundColor Green
