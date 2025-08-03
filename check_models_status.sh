#!/bin/bash

echo "🤖 ПРОВЕРКА СТАТУСА ML-МОДЕЛЕЙ"
echo "================================"

# Проверка здоровья API
echo "1️⃣ Проверка здоровья API..."
HEALTH_RESPONSE=$(curl -s http://localhost:8001/health)
if [ $? -eq 0 ]; then
    echo "✅ API здоров"
    MODELS_LOADED=$(echo $HEALTH_RESPONSE | grep -o '"models_loaded":[0-9]*' | cut -d':' -f2)
    echo "   Загружено моделей: $MODELS_LOADED"
else
    echo "❌ API недоступен"
    exit 1
fi

# Проверка статуса моделей
echo -e "\n2️⃣ Проверка статуса моделей..."
STATUS_RESPONSE=$(curl -s http://localhost:8001/models/status)
if [ $? -eq 0 ]; then
    echo "✅ Статус моделей получен"
    TOTAL_MODELS=$(echo $STATUS_RESPONSE | grep -o '"total_models":[0-9]*' | cut -d':' -f2)
    echo "   Всего моделей: $TOTAL_MODELS"
else
    echo "❌ Ошибка получения статуса моделей"
fi

# Тест прогнозирования
echo -e "\n3️⃣ Тест прогнозирования..."
FORECAST_RESPONSE=$(curl -s -X POST http://localhost:8001/forecast \
  -H "Content-Type: application/json" \
  -d '{"product_code":"30001","forecast_days":30}')

if [ $? -eq 0 ] && [ ! -z "$FORECAST_RESPONSE" ]; then
    echo "✅ Прогноз получен"
    
    # Проверяем, какие модели используются
    MODELS_USED=$(echo $FORECAST_RESPONSE | grep -o '"models_used":\[[^]]*\]' | cut -d':' -f2)
    echo "   Используемые модели: $MODELS_USED"
    
    # Проверяем точность
    CONFIDENCE=$(echo $FORECAST_RESPONSE | grep -o '"confidence":[0-9.]*' | cut -d':' -f2)
    echo "   Точность: $CONFIDENCE"
    
    # Проверяем тип модели
    MODEL_TYPE=$(echo $FORECAST_RESPONSE | grep -o '"model_type":"[^"]*"' | cut -d'"' -f4)
    echo "   Тип модели: $MODEL_TYPE"
    
    # Определяем статус
    if echo "$MODELS_USED" | grep -q "fallback"; then
        echo "⚠️  СТАТУС: Используется fallback режим (ML-модели не загружены)"
    else
        echo "✅ СТАТУС: Используются ML-модели!"
    fi
else
    echo "❌ Ошибка получения прогноза"
fi

# Проверка логов
echo -e "\n4️⃣ Проверка логов загрузки моделей..."
echo "   Последние логи:"
docker-compose logs forecast-api --tail=10 | grep -E "(model|load|error|numpy|INFO|ERROR)" | head -5

# Проверка файлов в контейнере
echo -e "\n5️⃣ Проверка файлов моделей..."
echo "   Файлы в /app/data/:"
docker exec forecast-api ls -la /app/data/ | grep -E "\.(pkl|joblib)" | head -3

# Итоговая оценка
echo -e "\n6️⃣ ИТОГОВАЯ ОЦЕНКА:"

if [ "$MODELS_LOADED" -gt 0 ]; then
    echo "✅ ML-модели загружены и работают"
    echo "   • Количество загруженных моделей: $MODELS_LOADED"
    echo "   • API прогнозирования работает"
    echo "   • Модели готовы к использованию"
elif [ "$MODELS_LOADED" -eq 0 ] && echo "$FORECAST_RESPONSE" | grep -q "fallback"; then
    echo "⚠️  ML-модели не загружены, используется fallback"
    echo "   • Проблема: Ошибка загрузки моделей"
    echo "   • Решение: Запустите ./fix_numpy_and_restart.sh"
    echo "   • API работает в резервном режиме"
else
    echo "❌ ML-модели не работают"
    echo "   • Проверьте логи на ошибки"
    echo "   • Запустите ./fix_numpy_and_restart.sh"
fi

echo -e "\n📅 Проверка выполнена: $(date)" 