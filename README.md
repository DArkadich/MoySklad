# 🤖 Система автоматизации закупок с ML-прогнозированием

Интеллектуальная система для автоматизации закупок в МойСклад с использованием машинного обучения для прогнозирования спроса.

## 🚀 Возможности

- **ML-прогнозирование спроса** на основе исторических данных
- **Автоматическая проверка остатков** раз в сутки
- **Создание заказов поставщикам** при низких остатках
- **REST API** для интеграции с внешними системами
- **Детальная аналитика** и отчеты
- **Мониторинг** и логирование всех операций

## 📊 Архитектура

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   МойСклад API  │    │  ML Forecast    │    │  Daily Auto-    │
│                 │◄──►│  API (8001)     │◄──►│  mation (6:00)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │     Redis       │    │    RabbitMQ     │
│   (5432)        │    │    (6379)       │    │   (5672/15672)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🛠 Установка и запуск

### 1. Предварительные требования

- Docker и Docker Compose
- Токен API МойСклад
- Python 3.8+

### 2. Настройка

Создайте файл `.env` в корневой папке:

```bash
# Токен API МойСклад
MOYSKLAD_API_TOKEN=your_moysklad_api_token_here

# Настройки базы данных
POSTGRES_DB=moysklad
POSTGRES_USER=moysklad
POSTGRES_PASSWORD=moysklad123

# Настройки Redis
REDIS_URL=redis://redis:6379

# Настройки RabbitMQ
RABBITMQ_URL=amqp://moysklad:moysklad123@rabbitmq:5672/
```

### 3. Запуск системы

```bash
# Сделайте скрипт исполняемым
chmod +x start_system.sh

# Запустите систему
./start_system.sh
```

### 4. Проверка работы

```bash
# Проверка статуса контейнеров
docker-compose ps

# Проверка API
curl http://localhost:8001/health

# Просмотр логов
docker-compose logs forecast-api
```

## 📋 API Endpoints

### Прогнозирование спроса

```bash
# POST /forecast
curl -X POST "http://localhost:8001/forecast" \
  -H "Content-Type: application/json" \
  -d '{
    "product_code": "60800",
    "forecast_days": 30
  }'
```

**Ответ:**
```json
{
  "product_code": "60800",
  "current_stock": 15.5,
  "forecast_consumption": 0.0295,
  "days_until_oos": 525,
  "recommended_order": 0,
  "confidence": 0.8,
  "models_used": ["linear_regression", "random_forest"]
}
```

### Автоматическое создание заказа

```bash
# POST /auto-purchase
curl -X POST "http://localhost:8001/auto-purchase" \
  -H "Content-Type: application/json" \
  -d '{
    "product_code": "60800",
    "forecast_days": 30
  }'
```

### Проверка здоровья системы

```bash
# GET /health
curl http://localhost:8001/health
```

## 🔄 Ежедневная автоматизация

Система автоматически запускается каждый день в 6:00 и:

1. **Проверяет остатки** всех товаров в МойСклад
2. **Делает ML-прогноз** потребления для каждого товара
3. **Создает заказы** для товаров с низкими остатками
4. **Генерирует отчеты** о результатах

### Отчеты

- **Детальный отчет:** `/app/data/daily_report_YYYYMMDD.json`
- **Сводка:** `/app/data/daily_summary.json`
- **Логи автоматизации:** `/app/data/automation.log`

## 📊 ML-модели

### Обученные модели:
- **Линейная регрессия** (R²: 1.0000)
- **Случайный лес** (R²: 0.9948)

### Признаки для прогнозирования:
- Временные: год, квартал, месяц
- Продажи: общие продажи, продажи в день, дни с продажами
- Остатки: максимальные, минимальные, средние остатки
- Частота: частота продаж, доступность остатков

## 🛠 Разработка

### Структура проекта

```
services/moysklad-service/
├── app/
│   ├── api_forecast.py          # FastAPI для прогнозирования
│   ├── daily_automation.py      # Ежедневная автоматизация
│   ├── train_forecast_models.py # Обучение ML-моделей
│   ├── export_demands.py        # Экспорт данных из МойСклад
│   └── core/
│       └── config.py            # Настройки
├── data/                        # Данные и модели
├── Dockerfile                   # Docker образ
└── requirements.txt             # Зависимости
```

### Обучение моделей

```bash
# Обучение ML-моделей
docker-compose run --rm -w /app moysklad-service python app/train_forecast_models.py
```

### Тестирование API

```bash
# Запуск тестов
docker-compose run --rm -w /app moysklad-service python -m pytest tests/
```

## 📈 Мониторинг

### Логи

```bash
# Логи API
docker-compose logs forecast-api

# Логи автоматизации
docker-compose logs automation-cron

# Логи базы данных
docker-compose logs postgres
```

### Метрики

- Количество проверенных товаров
- Количество созданных заказов
- Точность прогнозов
- Время выполнения операций

## 🔧 Настройка

### Изменение расписания

Отредактируйте cron в `docker-compose.yml`:

```yaml
command: |
  sh -c "
    echo '0 6 * * * python /app/app/daily_automation.py >> /app/data/automation.log 2>&1' > /etc/crontabs/root &&
    crond -f -d 8
  "
```

### Настройка уведомлений

Добавьте в `.env`:

```bash
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## 🚨 Устранение неполадок

### API недоступен

```bash
# Проверка статуса контейнеров
docker-compose ps

# Перезапуск API
docker-compose restart forecast-api

# Просмотр логов
docker-compose logs forecast-api
```

### Ошибки подключения к МойСклад

1. Проверьте токен в `.env`
2. Убедитесь в правильности URL API
3. Проверьте лимиты API

### Проблемы с ML-моделями

```bash
# Переобучение моделей
docker-compose run --rm -w /app moysklad-service python app/train_forecast_models.py
```

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи: `docker-compose logs`
2. Убедитесь в корректности настроек в `.env`
3. Проверьте доступность API МойСклад
4. Обратитесь к документации МойСклад API

## 📄 Лицензия

MIT License
