#!/bin/bash

echo "🔧 ИСПРАВЛЕНИЕ ПРОБЛЕМЫ С NUMPY И ПЕРЕЗАПУСК"
echo "=============================================="

# Остановка всех сервисов
echo "🛑 Остановка всех сервисов..."
docker-compose down

# Очистка кэша Docker
echo "🧹 Очистка кэша Docker..."
docker system prune -f

# Удаление старых образов
echo "🗑️  Удаление старых образов..."
docker rmi $(docker images | grep moysklad | awk '{print $3}') 2>/dev/null || echo "   Нет старых образов для удаления"

# Пересборка образов с новыми зависимостями
echo "🔨 Пересборка образов с исправленными зависимостями..."
docker-compose build --no-cache forecast-api moysklad-service

# Запуск сервисов
echo "🚀 Запуск сервисов..."
docker-compose up -d

# Ожидание запуска
echo "⏳ Ожидание запуска сервисов..."
sleep 45

# Проверка статуса
echo "📊 Проверка статуса сервисов..."
docker-compose ps

# Проверка здоровья
echo "🔍 Проверка здоровья сервисов..."
echo "   forecast-api:"
curl -s http://localhost:8001/health | jq . 2>/dev/null || echo "   Недоступен"

echo "   moysklad-service:"
curl -s http://localhost:8000/health | jq . 2>/dev/null || echo "   Недоступен"

# Проверка загрузки моделей
echo "🤖 Проверка загрузки моделей..."
echo "   Логи загрузки моделей:"
docker-compose logs forecast-api --tail=15 | grep -E "(model|load|error|numpy)"

# Тест прогнозирования
echo "🧪 Тест прогнозирования..."
TEST_RESPONSE=$(curl -s -X POST http://localhost:8001/forecast \
  -H "Content-Type: application/json" \
  -d '{"product_code":"30001","forecast_days":30}' 2>/dev/null)

if [ $? -eq 0 ] && [ ! -z "$TEST_RESPONSE" ]; then
    echo "✅ Прогноз работает!"
    echo "   Ответ: $TEST_RESPONSE" | head -c 300
    echo "..."
    
    # Проверяем, используются ли ML-модели
    if echo "$TEST_RESPONSE" | grep -q '"models_used":\["fallback"\]'; then
        echo "⚠️  Используется fallback режим (ML-модели не загружены)"
    else
        echo "✅ Используются ML-модели!"
    fi
else
    echo "❌ Прогноз не работает"
    echo "   Ошибка: $TEST_RESPONSE"
fi

# Проверка моделей в контейнере
echo "📁 Проверка файлов моделей в контейнере..."
docker exec forecast-api ls -la /app/data/ | grep -E "\.(pkl|joblib)"

echo ""
echo "🎉 Исправление завершено!"
echo ""
echo "📋 Команды для проверки:"
echo "   • ./check_ml_production.sh - полная проверка"
echo "   • docker-compose logs forecast-api - логи сервиса"
echo "   • curl -s http://localhost:8001/health - проверка здоровья"
echo "   • curl -X POST http://localhost:8001/forecast - тест прогноза" 