#!/bin/bash
# Скрипт для копирования исторических данных на проде

echo "📊 Копирование исторических данных на проде..."

# Проверяем наличие файлов в репозитории
if [ ! -f "data/production_stock_data.csv" ]; then
    echo "❌ Файл data/production_stock_data.csv не найден!"
    echo "Попробуйте: git checkout data/production_stock_data.csv"
    exit 1
fi

# Копируем файлы в контейнер
echo "📁 Копируем данные в контейнер..."

# Создаем папку data в контейнере если её нет
docker exec forecast-api mkdir -p /app/data

# Копируем исторические данные
docker cp data/production_stock_data.csv forecast-api:/app/data/
docker cp data/accurate_consumption_results.csv forecast-api:/app/data/
docker cp data/universal_forecast_models.pkl forecast-api:/app/data/
docker cp data/universal_model_performance.csv forecast-api:/app/data/

# Проверяем что файлы скопировались
echo "✅ Проверяем копирование..."
docker exec forecast-api ls -la /app/data/

echo "🎯 Данные скопированы! Теперь можно запускать обучение:"
echo "docker exec -it forecast-api python3 train_models_in_container.py" 