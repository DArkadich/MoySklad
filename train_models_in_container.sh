#!/bin/bash

# Скрипт для обучения моделей на реальных данных внутри Docker контейнера

echo "🚀 Запуск обучения моделей на реальных данных из MoySklad..."

# Проверяем, запущены ли контейнеры
if ! docker ps | grep -q "moysklad-service"; then
    echo "❌ Контейнеры не запущены. Запускаем систему..."
    ./start_system.sh
    sleep 10
fi

# Запускаем обучение моделей внутри контейнера moysklad-service
echo "📦 Запуск обучения моделей в контейнере moysklad-service..."

docker exec -it moysklad-service python3 /app/train_models_in_container.py

if [ $? -eq 0 ]; then
    echo "✅ Обучение моделей завершено успешно!"
    echo "🔄 Перезапуск сервиса для загрузки новых моделей..."
    
    # Перезапускаем сервис для загрузки новых моделей
    docker restart moysklad-service
    
    echo "⏳ Ожидание запуска сервиса..."
    sleep 15
    
    # Проверяем статус моделей
    echo "🔍 Проверка статуса моделей..."
    curl -s http://localhost:8001/models/status | jq '.' 2>/dev/null || echo "Сервис еще запускается..."
    
    echo "🎉 Система готова к работе с реальными моделями!"
else
    echo "❌ Ошибка обучения моделей"
    echo "📋 Проверьте логи:"
    echo "   docker logs moysklad-service"
fi 