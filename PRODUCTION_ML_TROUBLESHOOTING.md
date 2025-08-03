# Устранение проблем с ML-моделями на продакшене

## Проблема: Модели не загружаются (models_loaded: 0)

### 1. Диагностика проблемы

```bash
# Проверка логов
docker-compose logs forecast-api | grep -E "(model|load|error)"

# Проверка файлов в контейнере
docker exec forecast-api ls -la /app/data/

# Проверка здоровья API
curl -s http://localhost:8001/health | jq .
```

### 2. Причина проблемы

**Проблема:** Код ищет модели в `/app/data/models/`, но файлы находятся в `/app/data/`

**Симптомы:**
- В логах: `"Директория моделей не найдена: /app/data/models"`
- В health check: `"models_loaded": 0`
- API работает, но модели не загружены

### 3. Решение

```bash
# Перезапуск с исправлениями
./restart_ml_fixed.sh

# Или ручная перезагрузка
docker-compose stop forecast-api moysklad-service
docker-compose build forecast-api moysklad-service
docker-compose up -d forecast-api moysklad-service
```

### 4. Проверка после исправления

```bash
# Проверка загрузки моделей
curl -s http://localhost:8001/health | jq .

# Тест прогнозирования
curl -X POST http://localhost:8001/forecast \
  -H "Content-Type: application/json" \
  -d '{"product_code":"30001","forecast_days":30}'
```

## Проблема: Сервисы перезапускаются (Restarting)

### 1. Проверка статуса системы

```bash
# Проверьте запущенные контейнеры
docker ps

# Проверьте все контейнеры (включая остановленные)
docker ps -a

# Проверьте логи системы
docker-compose logs
```

### 2. Решение проблем с перезапуском

Если сервисы `analytics-service` или `purchase-service` находятся в состоянии "Restarting":

```bash
# Перезапуск системы с исправлениями
./restart_system_fixed.sh

# Или ручная очистка и перезапуск
docker-compose down --remove-orphans
docker system prune -f
docker-compose build --no-cache
docker-compose up -d
```

### 3. Проверка конфигурации

```bash
# Проверьте переменные окружения
docker-compose config

# Проверьте логи конкретного сервиса
docker-compose logs analytics-service
docker-compose logs purchase-service
```

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
ls -la /app/data/

# Вход в контейнер для проверки
docker exec forecast-api ls -la /app/data/
```

### 2. Обучение моделей

```bash
# Обучение всех моделей
curl -X POST http://localhost:8001/retrain-all

# Обучение конкретной модели
curl -X POST http://localhost:8001/train \
  -H "Content-Type: application/json" \
  -d '{
    "product_code": "30001",
    "model_type": "ensemble",
    "force_retrain": true
  }'
```

### 3. Обновление данных

```bash
# Обновление данных для обучения
curl -X POST http://localhost:8001/data/update
```

## Проблема: Ошибки подключения к базе данных

### 1. Проверка подключения к PostgreSQL

```bash
# Проверьте статус PostgreSQL
docker ps | grep postgres

# Проверьте логи PostgreSQL
docker-compose logs postgres

# Подключение к базе данных
docker exec -it moysklad-postgres psql -U moysklad -d moysklad
```

### 2. Проверка подключения к Redis

```bash
# Проверьте статус Redis
docker ps | grep redis

# Проверьте логи Redis
docker-compose logs redis

# Подключение к Redis
docker exec -it moysklad-redis redis-cli
```

### 3. Проверка подключения к RabbitMQ

```bash
# Проверьте статус RabbitMQ
docker ps | grep rabbitmq

# Проверьте логи RabbitMQ
docker-compose logs rabbitmq

# Доступ к веб-интерфейсу RabbitMQ
# http://localhost:15672 (логин: moysklad, пароль: moysklad123)
```

## Проблема: Недостаточно памяти

### 1. Проверка использования ресурсов

```bash
# Проверьте использование памяти
docker stats

# Проверьте использование диска
docker system df
```

### 2. Очистка ресурсов

```bash
# Очистка неиспользуемых образов
docker image prune -f

# Очистка неиспользуемых контейнеров
docker container prune -f

# Полная очистка системы
docker system prune -af
```

## Проблема: Сетевые ошибки

### 1. Проверка сети Docker

```bash
# Проверьте сети Docker
docker network ls

# Проверьте конфигурацию сети
docker network inspect moysklad_moysklad-network
```

### 2. Пересоздание сети

```bash
# Удаление и пересоздание сети
docker-compose down
docker network prune -f
docker-compose up -d
```

## Полезные команды для диагностики

```bash
# Просмотр всех логов
docker-compose logs

# Просмотр логов конкретного сервиса
docker-compose logs [service-name]

# Просмотр логов в реальном времени
docker-compose logs -f [service-name]

# Проверка конфигурации
docker-compose config

# Перезапуск конкретного сервиса
docker-compose restart [service-name]

# Обновление образа сервиса
docker-compose pull [service-name]
docker-compose up -d [service-name]
``` 