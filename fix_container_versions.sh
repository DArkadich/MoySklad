#!/bin/bash

echo "🔧 ИСПРАВЛЕНИЕ ВЕРСИЙ БИБЛИОТЕК В КОНТЕЙНЕРЕ"
echo "=============================================="

# Остановка сервисов
echo "🛑 Остановка ML-сервисов..."
docker-compose stop forecast-api moysklad-service

# Очистка образов
echo "🧹 Очистка старых образов..."
docker rmi moysklad-forecast-api moysklad-moysklad-service 2>/dev/null || echo "   Образы не найдены"

# Обновление requirements.txt с совместимыми версиями
echo "📦 Обновление версий зависимостей..."

cat > services/moysklad-service/requirements.txt << 'EOF'
# Основные зависимости (совместимые версии)
pandas==2.1.4
numpy==1.26.2
scikit-learn==1.3.2
joblib==1.3.2
requests==2.31.0
httpx==0.24.1
aiohttp==3.8.5
python-dotenv==1.0.0
psycopg2-binary==2.9.7
redis==4.6.0
celery==5.3.1

# FastAPI и веб-сервер
fastapi==0.103.1
uvicorn[standard]==0.23.2
pydantic==2.3.0

# Логирование и мониторинг
structlog==23.1.0
prometheus-client==0.17.1

# Утилиты
python-dateutil==2.8.2
pytz==2023.3
EOF

echo "✅ requirements.txt обновлен"

# Пересборка образов
echo "🔨 Пересборка образов с новыми версиями..."
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

# Проверка загрузки моделей
echo "🤖 Проверка загрузки моделей..."
echo "   Логи загрузки моделей:"
docker-compose logs forecast-api --tail=15 | grep -E "(model|load|error|numpy|INFO|ERROR)" | head -5

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

# Проверка версий в контейнере
echo "📦 Проверка версий в контейнере..."
echo "   NumPy версия:"
docker exec forecast-api python -c "import numpy; print(numpy.__version__)" 2>/dev/null || echo "   Недоступен"

echo "   Scikit-learn версия:"
docker exec forecast-api python -c "import sklearn; print(sklearn.__version__)" 2>/dev/null || echo "   Недоступен"

echo ""
echo "🎉 Исправление версий завершено!"
echo ""
echo "📋 Команды для проверки:"
echo "   • ./check_models_status.sh - проверка статуса моделей"
echo "   • docker-compose logs forecast-api - логи сервиса"
echo "   • curl -s http://localhost:8001/health - проверка здоровья" 