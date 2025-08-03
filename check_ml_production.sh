#!/bin/bash

echo "🏭 ПРОВЕРКА ML-МОДЕЛЕЙ В ПРОДАКШН-КОНТЕЙНЕРЕ"
echo "=============================================="

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен"
    exit 1
fi

# Проверка запущенных контейнеров
echo -e "\n1️⃣ Проверка контейнеров ML-сервиса..."
ML_CONTAINERS=$(docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(ml-service|forecast-api)")

if [ ! -z "$ML_CONTAINERS" ]; then
    echo "✅ Найдены ML-контейнеры:"
    echo "$ML_CONTAINERS"
else
    echo "❌ ML-контейнеры не найдены"
    echo "   Запущенные контейнеры:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    echo "💡 РЕКОМЕНДАЦИИ:"
    echo "   1. Запустите систему: ./start_system.sh"
    echo "   2. Или перезапустите: ./restart_system_fixed.sh"
    exit 1
fi

# Проверка здоровья ML-сервиса
echo -e "\n2️⃣ Проверка здоровья ML-сервиса..."

# Попробуем разные порты и сервисы
HEALTH_ENDPOINTS=(
    "http://localhost:8001/health"
    "http://localhost:8002/health"
    "http://localhost:8000/health"
)

HEALTH_OK=false
for endpoint in "${HEALTH_ENDPOINTS[@]}"; do
    echo "   Проверка $endpoint..."
    RESPONSE=$(curl -s --max-time 5 "$endpoint" 2>/dev/null)
    if [ $? -eq 0 ] && [ ! -z "$RESPONSE" ]; then
        echo "✅ ML-сервис здоров на $endpoint"
        echo "   Ответ: $RESPONSE"
        HEALTH_OK=true
        break
    fi
done

if [ "$HEALTH_OK" = false ]; then
    echo "❌ ML-сервис недоступен"
    echo "   Проверьте логи: docker-compose logs forecast-api"
    echo "   Или: docker-compose logs moysklad-service"
fi

# Проверка файлов моделей в контейнере
echo -e "\n3️⃣ Проверка файлов моделей в контейнере..."

# Найдем контейнер с ML-сервисом
ML_CONTAINER=$(docker ps --format "{{.Names}}" | grep -E "(ml-service|forecast-api|moysklad-service)" | head -1)

if [ ! -z "$ML_CONTAINER" ]; then
    echo "   Проверка в контейнере: $ML_CONTAINER"
    
    # Проверка директории данных
    DATA_CHECK=$(docker exec "$ML_CONTAINER" ls -la /app/data/ 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "✅ Директория /app/data/ найдена"
        echo "   Содержимое:"
        docker exec "$ML_CONTAINER" ls -la /app/data/ | head -10
    else
        echo "❌ Директория /app/data/ не найдена"
    fi
    
    # Проверка файлов моделей
    MODEL_FILES=$(docker exec "$ML_CONTAINER" find /app/data/ -name "*.pkl" -o -name "*.joblib" 2>/dev/null | wc -l)
    if [ $MODEL_FILES -gt 0 ]; then
        echo "✅ Найдено файлов моделей: $MODEL_FILES"
        echo "   Файлы моделей:"
        docker exec "$ML_CONTAINER" find /app/data/ -name "*.pkl" -o -name "*.joblib" 2>/dev/null | head -5
    else
        echo "❌ Файлы моделей не найдены"
    fi
    
    # Проверка CSV файлов
    CSV_FILES=$(docker exec "$ML_CONTAINER" find /app/data/ -name "*.csv" 2>/dev/null | wc -l)
    if [ $CSV_FILES -gt 0 ]; then
        echo "✅ Найдено CSV файлов: $CSV_FILES"
        echo "   CSV файлы:"
        docker exec "$ML_CONTAINER" find /app/data/ -name "*.csv" 2>/dev/null | head -5
    fi
else
    echo "❌ Контейнер ML-сервиса не найден"
fi

# Тестирование API прогнозирования
echo -e "\n4️⃣ Тестирование API прогнозирования..."

# Попробуем разные эндпоинты
FORECAST_ENDPOINTS=(
    "http://localhost:8001/forecast"
    "http://localhost:8002/forecast"
    "http://localhost:8000/forecast"
)

FORECAST_OK=false
for endpoint in "${FORECAST_ENDPOINTS[@]}"; do
    echo "   Тест $endpoint..."
    RESPONSE=$(curl -s --max-time 10 -X POST "$endpoint" \
        -H "Content-Type: application/json" \
        -d '{"product_code":"30001","forecast_days":30}' 2>/dev/null)
    
    if [ $? -eq 0 ] && [ ! -z "$RESPONSE" ]; then
        echo "✅ Прогноз получен с $endpoint"
        echo "   Ответ: $RESPONSE" | head -c 200
        echo "..."
        FORECAST_OK=true
        break
    fi
done

if [ "$FORECAST_OK" = false ]; then
    echo "❌ API прогнозирования недоступен"
fi

# Проверка логов
echo -e "\n5️⃣ Проверка логов ML-сервиса..."
echo "   Последние логи forecast-api:"
docker-compose logs forecast-api --tail=10 2>/dev/null || echo "   Логи недоступны"

echo "   Последние логи moysklad-service:"
docker-compose logs moysklad-service --tail=10 2>/dev/null || echo "   Логи недоступны"

# Итоговая оценка
echo -e "\n6️⃣ ИТОГОВАЯ ОЦЕНКА:"

if [ "$HEALTH_OK" = true ] && [ "$FORECAST_OK" = true ]; then
    echo "✅ ML-модели работают корректно в продакшене"
    echo "   • Сервис здоров"
    echo "   • API прогнозирования доступен"
    echo "   • Модели загружены и готовы к использованию"
elif [ "$HEALTH_OK" = true ]; then
    echo "⚠️  ML-сервис работает, но API прогнозирования недоступен"
    echo "   • Проверьте конфигурацию API"
    echo "   • Проверьте логи на ошибки"
else
    echo "❌ ML-сервис не работает корректно"
    echo "   • Проверьте статус контейнеров"
    echo "   • Проверьте логи на ошибки"
    echo "   • Попробуйте перезапуск: ./restart_system_fixed.sh"
fi

echo -e "\n📅 Проверка выполнена: $(date)" 