# setup.ps1 — Быстрый старт АСУ ПГР AI-бота (CPU)
# Запусти один раз — и всё готово к работе и тестам

Write-Host "=== АСУ ПГР AI-бот: быстрый старт (CPU) ===" -ForegroundColor Cyan

# 1. Проверяем .env
if (-not (Test-Path ".env")) {
    Write-Host "[1/4] Создаю .env..." -ForegroundColor Yellow
    $apiKey = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
    "API_KEY=$apiKey" | Out-File -FilePath ".env" -Encoding utf8
    Write-Host "       API_KEY сгенерирован: $apiKey" -ForegroundColor Green
} else {
    Write-Host "[1/4] .env уже есть" -ForegroundColor Green
}

# 2. Собираем образ (один раз)
Write-Host "[2/4] Сборка образа ai-bot..." -ForegroundColor Yellow
docker compose build ai-bot
if ($LASTEXITCODE -ne 0) {
    Write-Host "ОШИБКА сборки!" -ForegroundColor Red
    exit 1
}

# 3. Запускаем всё
Write-Host "[3/4] Запуск контейнеров..." -ForegroundColor Yellow
docker compose up -d ollama redis
Start-Sleep -Seconds 5

# 4. Качаем модель в Ollama (если ещё нет)
Write-Host "[4/4] Проверка модели phi4-mini в Ollama..." -ForegroundColor Yellow
$models = docker exec pgr-ollama ollama list 2>$null
if ($models -notmatch "phi4-mini") {
    Write-Host "       Качаю phi4-mini (это один раз)..." -ForegroundColor Yellow
    docker exec pgr-ollama ollama pull phi4-mini
}

# Запускаем ai-bot
docker compose up -d ai-bot

Write-Host ""
Write-Host "=== ГОТОВО! ===" -ForegroundColor Green
Write-Host "AI-бот:    http://localhost:8000" -ForegroundColor Cyan
Write-Host "Health:    http://localhost:8000/health" -ForegroundColor Cyan
Write-Host "Документация: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Правишь код — бот перезагружается сам (--reload)." -ForegroundColor Gray
Write-Host "Остановить:  docker compose down" -ForegroundColor Gray
Write-Host "Перезапуск:  docker compose restart ai-bot" -ForegroundColor Gray
Write-Host "Логи:        docker compose logs -f ai-bot" -ForegroundColor Gray
