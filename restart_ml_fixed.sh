#!/bin/bash

echo "🔧 ПЕРЕЗАПУСК ML-СЕРВИСОВ С ИСПРАВЛЕНИЯМИ"
echo "=========================================="

# Остановка ML-сервисов
echo "🛑 Остановка ML-сервисов..."
docker-compose stop forecast-api moysklad-service

# Пересборка образов с исправлениями
echo "🔨 Пересборка образов..."
docker-compose build forecast-api moysklad-service

# Запуск сервисов
echo "🚀 Запуск ML-сервисов..."
docker-compose up -d forecast-api moysklad-service

# Ожидание запуска
echo "⏳ Ожидание запуска сервисов..."
sleep 30

# Проверка статуса
echo "📊 Проверка статуса сервисов..."
docker-compose ps forecast-api moysklad-service

# Проверка здоровья
echo "🔍 Проверка здоровья сервисов..."
echo "   forecast-api:"
curl -s http://localhost:8001/health | jq . 2>/dev/null || echo "   Недоступен"

echo "   moysklad-service:"
curl -s http://localhost:8000/health | jq . 2>/dev/null || echo "   Недоступен"

# Проверка загрузки моделей
echo "🤖 Проверка загрузки моделей..."
echo "   Логи загрузки моделей:"
docker-compose logs forecast-api --tail=10 | grep -E "(model|load|error)"

# Тест прогнозирования
echo "🧪 Тест прогнозирования..."
TEST_RESPONSE=$(curl -s -X POST http://localhost:8001/forecast \
  -H "Content-Type: application/json" \
  -d '{"product_code":"30001","forecast_days":30}' 2>/dev/null)

if [ $? -eq 0 ] && [ ! -z "$TEST_RESPONSE" ]; then
    echo "✅ Прогноз работает!"
    echo "   Ответ: $TEST_RESPONSE" | head -c 200
    echo "..."
else
    echo "❌ Прогноз не работает"
    echo "   Ошибка: $TEST_RESPONSE"
fi

echo ""
echo "🎉 Перезапуск завершен!"
echo ""
echo "📋 Команды для проверки:"
echo "   • ./check_ml_production.sh - полная проверка"
echo "   • docker-compose logs forecast-api - логи сервиса"
echo "   • curl -s http://localhost:8001/health - проверка здоровья" 