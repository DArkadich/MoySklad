#!/bin/bash

echo "🐳 БЫСТРАЯ ПРОВЕРКА ML-МОДЕЛЕЙ В DOCKER"
echo "=========================================="

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен"
    exit 1
fi

# Проверка запущенных контейнеров
echo -e "\n1️⃣ Проверка Docker контейнеров..."
if docker ps | grep -q ml-service; then
    echo "✅ ML-сервис запущен в Docker"
    CONTAINER_ID=$(docker ps | grep ml-service | awk '{print $1}')
    echo "   ID контейнера: $CONTAINER_ID"
else
    echo "❌ ML-сервис не найден в запущенных контейнерах"
    echo "   Запущенные контейнеры:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    echo "💡 РЕКОМЕНДАЦИИ:"
    echo "   1. Запустите систему: ./start_system.sh"
    echo "   2. Или запустите только ML-сервис: docker-compose up -d ml-service"
    exit 1
fi

# Проверка здоровья ML-сервиса через контейнер
echo -e "\n2️⃣ Проверка здоровья ML-сервиса..."
HEALTH_RESPONSE=$(docker exec ml-service curl -s http://localhost:8002/health 2>/dev/null)

if [ $? -eq 0 ] && [ ! -z "$HEALTH_RESPONSE" ]; then
    echo "✅ ML-сервис здоров"
    MODELS_LOADED=$(echo $HEALTH_RESPONSE | grep -o '"models_loaded":[0-9]*' | cut -d':' -f2)
    echo "   Загружено моделей: $MODELS_LOADED"
else
    echo "❌ ML-сервис недоступен"
    echo "   Проверьте логи: docker logs ml-service"
    exit 1
fi

# Проверка статуса моделей через контейнер
echo -e "\n3️⃣ Получение статуса моделей..."
STATUS_RESPONSE=$(docker exec ml-service curl -s http://localhost:8002/models/status 2>/dev/null)

if [ $? -eq 0 ] && [ ! -z "$STATUS_RESPONSE" ]; then
    echo "✅ Статус моделей получен"
    TOTAL_MODELS=$(echo $STATUS_RESPONSE | grep -o '"total_models":[0-9]*' | cut -d':' -f2)
    AVG_ACCURACY=$(echo $STATUS_RESPONSE | grep -o '"average_accuracy":[0-9.]*' | cut -d':' -f2)
    
    echo "   Всего моделей: $TOTAL_MODELS"
    if [ ! -z "$AVG_ACCURACY" ]; then
        echo "   Средняя точность: $(echo "scale=2; $AVG_ACCURACY * 100" | bc)%"
    fi
else
    echo "❌ Ошибка получения статуса моделей"
fi

# Проверка файлов моделей в контейнере
echo -e "\n4️⃣ Проверка файлов моделей в контейнере..."
MODEL_FILES=$(docker exec ml-service ls -la /app/data/models/ 2>/dev/null | grep -E "\.(pkl|joblib)$" | wc -l)

if [ $? -eq 0 ]; then
    echo "✅ Директория моделей найдена"
    echo "   Файлов моделей: $MODEL_FILES"
    
    if [ $MODEL_FILES -gt 0 ]; then
        echo "   Примеры файлов:"
        docker exec ml-service ls -la /app/data/models/ | grep -E "\.(pkl|joblib)$" | head -3 | while read file; do
            echo "     $(basename "$file")"
        done
    fi
else
    echo "❌ Директория моделей не найдена"
fi

# Тестирование прогноза через контейнер
echo -e "\n5️⃣ Тестирование прогноза..."
TEST_PRODUCT="30001"
FORECAST_RESPONSE=$(docker exec ml-service curl -s -X POST http://localhost:8002/forecast \
  -H "Content-Type: application/json" \
  -d "{\"product_id\":\"$TEST_PRODUCT\",\"forecast_days\":30}" 2>/dev/null)

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

# Проверка ресурсов контейнера
echo -e "\n6️⃣ Проверка ресурсов контейнера..."
RESOURCE_STATS=$(docker stats ml-service --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" 2>/dev/null)

if [ $? -eq 0 ]; then
    echo "📊 Статистика ресурсов:"
    echo "$RESOURCE_STATS" | while read line; do
        if [ ! -z "$line" ]; then
            echo "   $line"
        fi
    done
else
    echo "❌ Ошибка получения статистики ресурсов"
fi

# Проверка логов
echo -e "\n7️⃣ Проверка логов ML-сервиса..."
RECENT_LOGS=$(docker logs --tail 5 ml-service 2>/dev/null)

if [ $? -eq 0 ]; then
    echo "📄 Последние 5 строк логов:"
    echo "$RECENT_LOGS" | while read line; do
        if [ ! -z "$line" ]; then
            echo "   $line"
        fi
    done
    
    # Проверяем наличие ошибок
    ERROR_COUNT=$(docker logs ml-service 2>&1 | grep -i "error\|exception" | wc -l)
    if [ $ERROR_COUNT -gt 0 ]; then
        echo "⚠️ Найдено $ERROR_COUNT строк с ошибками"
    fi
else
    echo "❌ Ошибка получения логов"
fi

# Итоговый статус
echo -e "\n=========================================="
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

echo -e "\n💡 Для детальной проверки запустите: python3 check_ml_docker.py" 