@echo off
echo.
echo ================================
echo Запуск фронтенда в Docker
echo Development режим
echo ================================
echo.
echo Приложение будет доступно на: http://localhost:3000
echo.
echo ⚠️  Убедитесь, что backend запущен на http://0.0.0.0:8001
echo.
pause

docker-compose -f docker-compose.dev.yml up --build

