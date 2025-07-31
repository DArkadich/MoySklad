#!/bin/bash

echo "🚀 Запуск системы автоматизации закупок с ML-прогнозированием..."

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo "Создайте файл .env с настройками:"
    echo "MOYSKLAD_API_TOKEN=your_token_here"
    exit 1
fi

# Загружаем переменные окружения
source .env

# Проверяем токен
if [ -z "$MOYSKLAD_API_TOKEN" ]; then
    echo "❌ MOYSKLAD_API_TOKEN не настроен в .env"
    exit 1
fi

echo "✅ Токен МойСклад настроен"

# Останавливаем существующие контейнеры
echo "🛑 Остановка существующих контейнеров..."
docker-compose down

# Создаем папку для данных
mkdir -p data

# Запускаем систему
echo "🚀 Запуск системы..."
docker-compose up -d

# Ждем запуска сервисов
echo "⏳ Ожидание запуска сервисов..."
sleep 30

# Проверяем статус
echo "📊 Проверка статуса сервисов..."
docker-compose ps

# Проверяем API
echo "🔍 Проверка API..."
curl -s http://localhost:8001/health || echo "❌ API недоступен"

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