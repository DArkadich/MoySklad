#!/bin/bash

echo "🔍 ПРОВЕРКА ML-МОДЕЛЕЙ В ПРОДАКШНЕ"
echo "===================================="
echo "📅 Время проверки: $(date)"
echo ""

# 1. Проверка статуса контейнеров
echo "1️⃣ ПРОВЕРКА СТАТУСА КОНТЕЙНЕРОВ"
echo "--------------------------------"

if command -v docker &> /dev/null; then
    echo "✅ Docker доступен"
    
    # Проверяем запущенные контейнеры
    ML_CONTAINERS=$(docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(ml-service|forecast-api|moysklad-service)")
    
    if [ ! -z "$ML_CONTAINERS" ]; then
        echo "✅ Найдены ML-контейнеры:"
        echo "$ML_CONTAINERS"
    else
        echo "❌ ML-контейнеры не найдены"
        echo "   Запущенные контейнеры:"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        echo ""
        echo "💡 РЕКОМЕНДАЦИИ:"
        echo "   1. Запустите систему: ./start_system_optimized.sh"
        echo "   2. Или перезапустите: ./restart_system_fixed.sh"
        exit 1
    fi
else
    echo "❌ Docker не установлен или недоступен"
    exit 1
fi

# 2. Проверка здоровья ML-сервисов
echo ""
echo "2️⃣ ПРОВЕРКА ЗДОРОВЬЯ ML-СЕРВИСОВ"
echo "--------------------------------"

HEALTH_ENDPOINTS=(
    "http://localhost:8001/health"
    "http://localhost:8002/health"
    "http://localhost:8000/health"
)

WORKING_SERVICES=()
for endpoint in "${HEALTH_ENDPOINTS[@]}"; do
    echo "   Проверка $endpoint..."
    if curl -s --max-time 5 "$endpoint" > /dev/null; then
        echo "   ✅ Доступен"
        WORKING_SERVICES+=("$endpoint")
    else
        echo "   ❌ Недоступен"
    fi
done

if [ ${#WORKING_SERVICES[@]} -eq 0 ]; then
    echo "❌ Нет доступных ML-сервисов!"
    echo "   Проверьте логи: docker-compose logs"
    exit 1
fi

# 3. Проверка статуса моделей
echo ""
echo "3️⃣ ПРОВЕРКА СТАТУСА МОДЕЛЕЙ"
echo "----------------------------"

MODELS_STATUS=""
for service in "${WORKING_SERVICES[@]}"; do
    base_url=$(echo "$service" | sed 's|/health||')
    echo "   Проверка статуса моделей на $base_url..."
    
    if curl -s --max-time 5 "$base_url/models/status" > /dev/null; then
        MODELS_STATUS=$(curl -s --max-time 5 "$base_url/models/status")
        echo "   ✅ Статус моделей получен"
        break
    else
        echo "   ❌ Статус моделей недоступен"
    fi
done

if [ ! -z "$MODELS_STATUS" ]; then
    echo "📊 СТАТУС МОДЕЛЕЙ:"
    echo "$MODELS_STATUS" | jq . 2>/dev/null || echo "$MODELS_STATUS"
else
    echo "❌ Статус моделей не получен"
fi

# 4. Проверка загруженных моделей
echo ""
echo "4️⃣ ПРОВЕРКА ЗАГРУЖЕННЫХ МОДЕЛЕЙ"
echo "--------------------------------"

MODELS_LOADED=0
for service in "${WORKING_SERVICES[@]}"; do
    base_url=$(echo "$service" | sed 's|/health||')
    echo "   Проверка health на $base_url..."
    
    HEALTH_RESPONSE=$(curl -s --max-time 5 "$service")
    if [ ! -z "$HEALTH_RESPONSE" ]; then
        # Извлекаем количество загруженных моделей
        MODELS_COUNT=$(echo "$HEALTH_RESPONSE" | grep -o '"models_loaded":[0-9]*' | cut -d':' -f2)
        if [ ! -z "$MODELS_COUNT" ]; then
            MODELS_LOADED=$MODELS_COUNT
            echo "   ✅ Загружено моделей: $MODELS_LOADED"
            break
        fi
    fi
done

# 5. Проверка файлов моделей в контейнере
echo ""
echo "5️⃣ ПРОВЕРКА ФАЙЛОВ МОДЕЛЕЙ В КОНТЕЙНЕРЕ"
echo "----------------------------------------"

# Найдем контейнер с ML-сервисом
ML_CONTAINER=$(docker ps --format "{{.Names}}" | grep -E "(ml-service|forecast-api|moysklad-service)" | head -1)

if [ ! -z "$ML_CONTAINER" ]; then
    echo "   Проверка в контейнере: $ML_CONTAINER"
    
    # Проверка директории данных
    if docker exec "$ML_CONTAINER" ls -la /app/data/ > /dev/null 2>&1; then
        echo "   ✅ Директория /app/data/ найдена"
        
        # Проверка файлов моделей
        MODEL_FILES=$(docker exec "$ML_CONTAINER" find /app/data/ -name "*.pkl" -o -name "*.joblib" 2>/dev/null | wc -l)
        if [ $MODEL_FILES -gt 0 ]; then
            echo "   ✅ Найдено файлов моделей: $MODEL_FILES"
            echo "   Файлы моделей:"
            docker exec "$ML_CONTAINER" find /app/data/ -name "*.pkl" -o -name "*.joblib" 2>/dev/null | head -5
        else
            echo "   ❌ Файлы моделей не найдены"
        fi
        
        # Проверка CSV файлов
        CSV_FILES=$(docker exec "$ML_CONTAINER" find /app/data/ -name "*.csv" 2>/dev/null | wc -l)
        if [ $CSV_FILES -gt 0 ]; then
            echo "   ✅ Найдено CSV файлов: $CSV_FILES"
        fi
    else
        echo "   ❌ Директория /app/data/ не найдена"
    fi
else
    echo "❌ Контейнер ML-сервиса не найден"
fi

# 6. Тестирование API прогнозирования
echo ""
echo "6️⃣ ТЕСТИРОВАНИЕ API ПРОГНОЗИРОВАНИЯ"
echo "-----------------------------------"

FORECAST_WORKING=false
TEST_PRODUCTS=("30001" "60800" "360360")

for service in "${WORKING_SERVICES[@]}"; do
    base_url=$(echo "$service" | sed 's|/health||')
    
    for product_code in "${TEST_PRODUCTS[@]}"; do
        echo "   Тест прогноза для продукта $product_code на $base_url..."
        
        FORECAST_RESPONSE=$(curl -s --max-time 10 -X POST "$base_url/forecast" \
            -H "Content-Type: application/json" \
            -d "{\"product_code\":\"$product_code\",\"forecast_days\":30}" 2>/dev/null)
        
        if [ $? -eq 0 ] && [ ! -z "$FORECAST_RESPONSE" ]; then
            echo "   ✅ Прогноз получен для продукта $product_code"
            echo "   Ответ: $FORECAST_RESPONSE" | head -c 200
            echo "..."
            FORECAST_WORKING=true
            break 2
        else
            echo "   ❌ Прогноз недоступен"
        fi
    done
done

# 7. Итоговая оценка
echo ""
echo "7️⃣ ИТОГОВАЯ ОЦЕНКА"
echo "-------------------"

if [ $MODELS_LOADED -gt 0 ]; then
    echo "✅ ML-МОДЕЛИ ОБУЧЕНЫ И ГОТОВЫ К ИСПОЛЬЗОВАНИЮ"
    echo "   • Загружено моделей: $MODELS_LOADED"
    
    if [ "$FORECAST_WORKING" = true ]; then
        echo "   • API прогнозирования работает"
    else
        echo "   • ⚠️ API прогнозирования требует проверки"
    fi
    
elif [ ${#WORKING_SERVICES[@]} -gt 0 ]; then
    echo "⚠️ ML-СЕРВИСЫ РАБОТАЮТ, НО МОДЕЛИ НЕ ЗАГРУЖЕНЫ"
    echo "   • Необходимо обучить модели"
    echo "   • Запустите: docker exec forecast-api python3 train_models_in_container.py"
    
else
    echo "❌ ML-СЕРВИСЫ НЕ РАБОТАЮТ"
    echo "   • Проверьте статус контейнеров"
    echo "   • Запустите систему: ./start_system_optimized.sh"
fi

# 8. Рекомендации
echo ""
echo "8️⃣ РЕКОМЕНДАЦИИ"
echo "---------------"

if [ $MODELS_LOADED -eq 0 ]; then
    echo "🚀 Для обучения моделей:"
    echo "   1. Проверьте наличие исторических данных:"
    echo "      docker exec forecast-api ls -la /app/data/"
    echo "   2. Запустите обучение:"
    echo "      docker exec forecast-api python3 train_models_in_container.py"
    echo "   3. Проверьте логи обучения:"
    echo "      docker-compose logs forecast-api"
fi

echo "🔧 Для диагностики:"
echo "   1. Статус контейнеров: docker ps"
echo "   2. Логи сервисов: docker-compose logs"
echo "   3. Файлы в контейнере: docker exec forecast-api ls -la /app/data/"

echo ""
echo "📅 Проверка завершена: $(date)"
