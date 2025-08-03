#!/bin/bash

echo "🔧 Перезапуск системы с исправлениями..."

# Остановка всех контейнеров
echo "🛑 Остановка всех контейнеров..."
docker-compose down

# Удаление orphan контейнеров
echo "🧹 Удаление orphan контейнеров..."
docker-compose down --remove-orphans

# Очистка неиспользуемых ресурсов
echo "🧹 Очистка неиспользуемых ресурсов..."
docker system prune -f

# Пересборка образов
echo "🔨 Пересборка образов..."
docker-compose build --no-cache

# Запуск системы
echo "🚀 Запуск системы..."
docker-compose up -d

# Ожидание запуска
echo "⏳ Ожидание запуска сервисов..."
sleep 45

# Проверка статуса
echo "📊 Проверка статуса сервисов..."
docker-compose ps

# Проверка логов проблемных сервисов
echo "📝 Проверка логов analytics-service..."
docker-compose logs analytics-service --tail=20

echo "📝 Проверка логов purchase-service..."
docker-compose logs purchase-service --tail=20

echo "🔍 Проверка API..."
curl -s http://localhost:8001/health || echo "❌ API недоступен"

echo ""
echo "🎉 Система перезапущена с исправлениями!"
echo ""
echo "📋 Доступные сервисы:"
echo "  • API прогнозирования: http://localhost:8001"
echo "  • Analytics Service: http://localhost:8004"
echo "  • Purchase Service: http://localhost:8005"
echo "  • RabbitMQ Management: http://localhost:15672"
echo "  • PostgreSQL: localhost:5432"
echo "  • Redis: localhost:6379" 