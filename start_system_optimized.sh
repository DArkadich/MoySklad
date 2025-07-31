#!/bin/bash

echo "🚀 Запуск оптимизированной системы автоматизации закупок..."
echo "📊 Версия: 2.0 (оптимизированная)"

# Загрузка переменных из .env файла
if [ -f ".env" ]; then
    echo "📄 Загружаем переменные из .env файла..."
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "⚠️  Файл .env не найден, используем переменные окружения"
fi

# Проверка токена МойСклад
if [ -z "$MOYSKLAD_API_TOKEN" ]; then
    echo "❌ MOYSKLAD_API_TOKEN не установлен"
    echo "   Создайте файл .env на основе env.example и укажите токен"
    echo "   cp env.example .env"
    echo "   # Затем отредактируйте .env и укажите ваш токен"
    exit 1
else
    echo "✅ Токен МойСклад настроен"
fi

# Остановка существующих контейнеров
echo "🛑 Остановка существующих контейнеров..."
docker-compose --env-file .env down

# Запуск системы
echo "🚀 Запуск системы..."
docker-compose --env-file .env up -d

# Ожидание запуска сервисов
echo "⏳ Ожидание запуска сервисов..."
sleep 10

# Проверка статуса сервисов
echo "📊 Проверка статуса сервисов..."
docker-compose --env-file .env ps

# Проверка API
echo "🔍 Проверка API..."
sleep 5

# Тест API
if command -v curl &> /dev/null; then
    API_RESPONSE=$(curl -s http://localhost:8001/health 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "✅ API доступен"
    else
        echo "❌ API недоступен"
    fi
else
    echo "⚠️  curl не найден, пропускаем проверку API"
fi

echo ""
echo "🎉 Система запущена!"
echo ""
echo "📋 Доступные сервисы:"
echo "  • API прогнозирования: http://localhost:8001"
echo "  • RabbitMQ Management: http://localhost:15672"
echo "  • PostgreSQL: localhost:5432"
echo "  • Redis: localhost:6379"
echo ""
echo "📝 Логи:"
echo "  • docker-compose logs forecast-api"
echo "  • docker-compose logs automation-cron"
echo ""
echo "🔄 Ежедневная автоматизация запускается в 6:00"
echo "📊 Отчеты сохраняются в папку ./data/"
echo ""
echo "🧪 Тестирование API:"
echo "  • python3 test_api_simple.py"
echo ""
echo "📝 Настройка:"
echo "  • Отредактируйте .env файл и укажите ваш токен МойСклад"
echo "  • nano .env"
echo "  • Измените MOYSKLAD_API_TOKEN=your_actual_token" 