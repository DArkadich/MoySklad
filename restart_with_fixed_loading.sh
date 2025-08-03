#!/bin/bash

echo "🔧 ПЕРЕЗАПУСК С ИСПРАВЛЕННОЙ ЗАГРУЗКОЙ МОДЕЛЕЙ"
echo "================================================"

# Остановка сервисов
echo "🛑 Остановка ML-сервисов..."
docker-compose stop forecast-api moysklad-service

# Пересборка образов с исправленным кодом
echo "🔨 Пересборка образов с исправленным кодом..."
docker-compose build --no-cache forecast-api moysklad-service

# Запуск сервисов
echo "🚀 Запуск сервисов..."
docker-compose up -d forecast-api moysklad-service

# Ожидание запуска
echo "⏳ Ожидание запуска сервисов..."
sleep 45

# Проверка здоровья
echo "🔍 Проверка здоровья сервисов..."
echo "   forecast-api:"
curl -s http://localhost:8001/health | jq . 2>/dev/null || echo "   Недоступен"

echo "   moysklad-service:"
curl -s http://localhost:8000/health | jq . 2>/dev/null || echo "   Недоступен"

# Проверка логов загрузки моделей
echo "🤖 Проверка логов загрузки моделей..."
echo "   Последние логи:"
docker-compose logs forecast-api --tail=20 | grep -E "(model|load|error|INFO|ERROR|WARNING)" | head -10

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
        echo "   Проверьте логи: docker-compose logs forecast-api"
    else
        echo "✅ Используются ML-модели!"
    fi
else
    echo "❌ Прогноз не работает"
    echo "   Ошибка: $TEST_RESPONSE"
fi

# Проверка статуса моделей
echo "📊 Проверка статуса моделей..."
STATUS_RESPONSE=$(curl -s http://localhost:8001/models/status 2>/dev/null)
if [ $? -eq 0 ] && [ ! -z "$STATUS_RESPONSE" ]; then
    echo "✅ Статус моделей получен"
    echo "   Ответ: $STATUS_RESPONSE"
else
    echo "❌ Ошибка получения статуса моделей"
fi

# Детальная проверка логов
echo "📝 Детальная проверка логов..."
echo "   Логи загрузки моделей:"
docker-compose logs forecast-api | grep -E "(Загружено моделей|Загружена модель|Ошибка загрузки)" | tail -5

echo ""
echo "🎉 Перезапуск с исправлениями завершен!"
echo ""
echo "📋 Команды для проверки:"
echo "   • ./check_models_status.sh - проверка статуса моделей"
echo "   • docker-compose logs forecast-api - полные логи"
echo "   • curl -s http://localhost:8001/health - проверка здоровья" 