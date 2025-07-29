#!/bin/bash

# Horiens Purchase Agent - Скрипт запуска
echo "🚀 Запуск Horiens Purchase Agent..."

# Проверка наличия Docker и Docker Compose
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Пожалуйста, установите Docker."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен. Пожалуйста, установите Docker Compose."
    exit 1
fi

# Проверка наличия .env файла
if [ ! -f .env ]; then
    echo "⚠️  Файл .env не найден. Создаю из примера..."
    cp env.example .env
    echo "📝 Пожалуйста, отредактируйте файл .env с вашими настройками"
    echo "   Особенно важно указать MOYSKLAD_API_TOKEN"
    read -p "Продолжить запуск? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Остановка существующих контейнеров
echo "🛑 Остановка существующих контейнеров..."
docker-compose down

# Сборка и запуск контейнеров
echo "🔨 Сборка и запуск контейнеров..."
docker-compose up -d --build

# Ожидание запуска сервисов
echo "⏳ Ожидание запуска сервисов..."
sleep 30

# Проверка статуса сервисов
echo "🔍 Проверка статуса сервисов..."
docker-compose ps

# Проверка здоровья API
echo "🏥 Проверка здоровья API..."
sleep 10

# Проверка доступности основных сервисов
echo "📊 Проверка доступности сервисов:"

# Purchase Service
if curl -s http://localhost:8001/health > /dev/null; then
    echo "✅ Purchase Service - доступен"
else
    echo "❌ Purchase Service - недоступен"
fi

# ML Service
if curl -s http://localhost:8002/health > /dev/null; then
    echo "✅ ML Service - доступен"
else
    echo "❌ ML Service - недоступен"
fi

# Grafana
if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ Grafana - доступен (admin/admin)"
else
    echo "❌ Grafana - недоступен"
fi

# RabbitMQ Management
if curl -s http://localhost:15672 > /dev/null; then
    echo "✅ RabbitMQ Management - доступен (guest/guest)"
else
    echo "❌ RabbitMQ Management - недоступен"
fi

echo ""
echo "🎉 Horiens Purchase Agent запущен!"
echo ""
echo "📋 Доступные сервисы:"
echo "   • Purchase Service API: http://localhost:8001"
echo "   • ML Service API: http://localhost:8002"
echo "   • Grafana Dashboard: http://localhost:3000 (admin/admin)"
echo "   • RabbitMQ Management: http://localhost:15672 (guest/guest)"
echo "   • Prometheus: http://localhost:9090"
echo ""
echo "📚 Документация API:"
echo "   • Purchase Service: http://localhost:8001/docs"
echo "   • ML Service: http://localhost:8002/docs"
echo ""
echo "🛑 Для остановки системы выполните: docker-compose down" 