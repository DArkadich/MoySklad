# Устранение проблем с ML-моделями на продакшене

## Проблема: ML-сервис недоступен

### 1. Проверка статуса системы

```bash
# Проверьте запущенные контейнеры
docker ps

# Проверьте все контейнеры (включая остановленные)
docker ps -a

# Проверьте логи системы
docker-compose logs
```

### 2. Запуск системы

```bash
# Запуск всей системы
./start_system.sh

# Или запуск только ML-сервиса
docker-compose up -d ml-service

# Проверка статуса после запуска
docker ps | grep ml-service
```

### 3. Проверка портов

```bash
# Проверьте, какие порты заняты
netstat -tlnp | grep 8002

# Или через docker
docker port ml-service
```

## Проблема: Отсутствует модуль aiohttp

### 1. Установка зависимостей

```bash
# Установка aiohttp
pip3 install aiohttp

# Или через python
python3 -m pip install aiohttp

# Установка всех зависимостей
pip3 install -r requirements.txt
```

### 2. Альтернативная проверка без aiohttp

Используйте упрощенный скрипт:

```bash
# Запуск упрощенной проверки
python3 check_ml_simple.py
```

Этот скрипт использует только `requests` (обычно уже установлен).

## Проблема: Модели не загружены

### 1. Проверка файлов моделей

```bash
# Проверьте наличие файлов моделей
ls -la /app/data/models/

# Вход в контейнер для проверки
docker exec -it ml-service ls -la /app/data/models/
```

### 2. Обучение моделей

```bash
# Обучение всех моделей
curl -X POST http://localhost:8002/retrain-all

# Обучение конкретной модели
curl -X POST http://localhost:8002/train \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "30001",
    "model_type": "ensemble",
    "force_retrain": true
  }'
```

### 3. Обновление данных

```bash
# Обновление данных для обучения
curl -X POST http://localhost:8002/data/update
```

## Быстрые команды для диагностики

### 1. Проверка здоровья системы (Docker)

```bash
# Проверка ML-моделей в Docker контейнере
./quick_ml_check_docker.sh

# Детальная проверка через Python
python3 check_ml_docker.py

# Упрощенная проверка (если нет зависимостей)
python3 check_ml_simple.py

# Проверка через curl в контейнере
docker exec ml-service curl http://localhost:8002/health
```

### 2. Проверка логов

```bash
# Логи ML-сервиса
docker logs ml-service

# Логи с последними записями
docker logs --tail 50 ml-service

# Логи с фильтрацией
docker logs ml-service | grep -i error
```

### 3. Перезапуск сервисов

```bash
# Перезапуск ML-сервиса
docker restart ml-service

# Перезапуск всей системы
docker-compose restart

# Полная перезагрузка
docker-compose down && docker-compose up -d
```

## Пошаговое решение проблем

### Шаг 1: Проверка системы

```bash
# 1. Проверьте статус Docker
docker --version
docker ps

# 2. Проверьте статус системы
./quick_ml_check.sh
```

### Шаг 2: Запуск системы (если не запущена)

```bash
# 1. Запустите систему
./start_system.sh

# 2. Подождите 30 секунд
sleep 30

# 3. Проверьте статус
docker ps | grep ml-service
```

### Шаг 3: Установка зависимостей (если нужно)

```bash
# 1. Установите aiohttp
pip3 install aiohttp

# 2. Проверьте установку
python3 -c "import aiohttp; print('aiohttp установлен')"
```

### Шаг 4: Обучение моделей (если не обучены)

```bash
# 1. Проверьте данные
ls -la data/

# 2. Обновите данные
curl -X POST http://localhost:8002/data/update

# 3. Обучите модели
curl -X POST http://localhost:8002/retrain-all

# 4. Подождите завершения обучения
sleep 60
```

### Шаг 5: Финальная проверка

```bash
# 1. Проверьте статус
python3 check_ml_simple.py

# 2. Тестируйте прогноз
curl -X POST http://localhost:8002/forecast \
  -H "Content-Type: application/json" \
  -d '{"product_id":"30001","forecast_days":30}'
```

## Автоматизация проверок

### Создание скрипта автоматической проверки

```bash
#!/bin/bash
# auto_ml_check.sh

echo "🔍 АВТОМАТИЧЕСКАЯ ПРОВЕРКА ML-СИСТЕМЫ"
echo "========================================"

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен"
    exit 1
fi

# Проверка системы
if ! ./quick_ml_check.sh; then
    echo "🔄 Попытка запуска системы..."
    ./start_system.sh
    sleep 30
    ./quick_ml_check.sh
fi

echo "✅ Проверка завершена"
```

### Настройка cron для регулярных проверок

```bash
# Добавьте в crontab
# Проверка каждые 6 часов
0 */6 * * * /path/to/MoySklad/auto_ml_check.sh >> /var/log/ml_check.log 2>&1
```

## Контакты и поддержка

### Логи для анализа

```bash
# Основные логи
docker logs ml-service > ml_service.log
docker logs api-gateway > api_gateway.log

# Логи с ошибками
docker logs ml-service 2>&1 | grep -i error > ml_errors.log
```

### Полезные команды

```bash
# Проверка ресурсов
docker stats ml-service

# Проверка сети
docker network ls
docker network inspect moy_sklad_default

# Проверка volumes
docker volume ls
docker volume inspect moy_sklad_data
```

### Экстренные меры

```bash
# Полная перезагрузка системы
docker-compose down
docker system prune -f
docker-compose up -d

# Проверка после перезагрузки
sleep 60
python3 check_ml_simple.py
``` 