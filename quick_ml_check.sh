#!/bin/bash

echo "🔍 БЫСТРАЯ ПРОВЕРКА ML-МОДЕЛЕЙ"
echo "=================================="

# Проверка здоровья ML-сервиса
echo -e "\n1️⃣ Проверка здоровья ML-сервиса..."
if curl -s http://localhost:8002/health > /dev/null; then
    echo "✅ ML-сервис доступен"
    HEALTH_RESPONSE=$(curl -s http://localhost:8002/health)
    MODELS_LOADED=$(echo $HEALTH_RESPONSE | grep -o '"models_loaded":[0-9]*' | cut -d':' -f2)
    echo "   Загружено моделей: $MODELS_LOADED"
else
    echo "❌ ML-сервис недоступен"
    echo "   Проверьте, что сервис запущен на порту 8002"
    exit 1
fi

# Проверка статуса моделей
echo -e "\n2️⃣ Получение статуса моделей..."
if curl -s http://localhost:8002/models/status > /dev/null; then
    echo "✅ Статус моделей получен"
    STATUS_RESPONSE=$(curl -s http://localhost:8002/models/status)
    TOTAL_MODELS=$(echo $STATUS_RESPONSE | grep -o '"total_models":[0-9]*' | cut -d':' -f2)
    AVG_ACCURACY=$(echo $STATUS_RESPONSE | grep -o '"average_accuracy":[0-9.]*' | cut -d':' -f2)
    
    echo "   Всего моделей: $TOTAL_MODELS"
    if [ ! -z "$AVG_ACCURACY" ]; then
        echo "   Средняя точность: $(echo "scale=2; $AVG_ACCURACY * 100" | bc)%"
    fi
else
    echo "❌ Ошибка получения статуса моделей"
fi

# Проверка файлов моделей
echo -e "\n3️⃣ Проверка файлов моделей..."
MODELS_DIR="/app/data/models"
if [ -d "$MODELS_DIR" ]; then
    MODEL_FILES=$(find "$MODELS_DIR" -name "*.pkl" -o -name "*.joblib" | wc -l)
    echo "✅ Директория моделей найдена"
    echo "   Файлов моделей: $MODEL_FILES"
    
    if [ $MODEL_FILES -gt 0 ]; then
        echo "   Примеры файлов:"
        find "$MODELS_DIR" -name "*.pkl" -o -name "*.joblib" | head -3 | while read file; do
            echo "     $(basename "$file")"
        done
    fi
else
    echo "❌ Директория моделей не найдена: $MODELS_DIR"
fi

# Тестирование прогноза
echo -e "\n4️⃣ Тестирование прогноза..."
TEST_PRODUCT="30001"
FORECAST_RESPONSE=$(curl -s -X POST http://localhost:8002/forecast \
  -H "Content-Type: application/json" \
  -d "{\"product_id\":\"$TEST_PRODUCT\",\"forecast_days\":30}")

if [ $? -eq 0 ] && [ ! -z "$FORECAST_RESPONSE" ]; then
    echo "✅ Прогноз получен для продукта $TEST_PRODUCT"
    DAILY_DEMAND=$(echo $FORECAST_RESPONSE | grep -o '"daily_demand":[0-9.]*' | cut -d':' -f2)
    ACCURACY=$(echo $FORECAST_RESPONSE | grep -o '"accuracy":[0-9.]*' | cut -d':' -f2)
    MODEL_TYPE=$(echo $FORECAST_RESPONSE | grep -o '"model_type":"[^"]*"' | cut -d'"' -f4)
    
    echo "   Дневной спрос: $DAILY_DEMAND"
    if [ ! -z "$ACCURACY" ]; then
        echo "   Точность: $(echo "scale=2; $ACCURACY * 100" | bc)%"
    fi
    echo "   Модель: $MODEL_TYPE"
else
    echo "❌ Ошибка получения прогноза"
fi

# Итоговый статус
echo -e "\n=================================="
echo "📋 ИТОГОВЫЙ СТАТУС:"

if [ ! -z "$TOTAL_MODELS" ] && [ "$TOTAL_MODELS" -gt 0 ]; then
    echo "✅ ML-модели обучены и готовы к использованию"
    echo "   Загружено моделей: $TOTAL_MODELS"
    if [ ! -z "$AVG_ACCURACY" ]; then
        echo "   Средняя точность: $(echo "scale=2; $AVG_ACCURACY * 100" | bc)%"
    fi
elif [ ! -z "$MODELS_LOADED" ] && [ "$MODELS_LOADED" -gt 0 ]; then
    echo "✅ ML-сервис работает, модели загружены"
    echo "   Загружено моделей: $MODELS_LOADED"
else
    echo "⚠️ ML-сервис работает, но модели не загружены"
    echo "   Необходимо обучить модели"
fi

echo -e "\n💡 Для детальной проверки запустите: python check_ml_models.py" 