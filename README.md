# 🤖 Система автоматизации закупок с ML-прогнозированием

Интеллектуальная система для автоматизации закупок в МойСклад с использованием машинного обучения для прогнозирования спроса и оптимизации доставки.

## 🚀 Возможности

- **ML-прогнозирование спроса** на основе реальных данных из MoySklad API
- **Оптимизация доставки** с объединением поставок линз и растворов
- **Автоматическая проверка остатков** раз в сутки
- **Создание заказов поставщикам** при низких остатках
- **REST API** для интеграции с внешними системами
- **Детальная аналитика** и отчеты
- **Мониторинг** и логирование всех операций
- **Реальные данные** вместо синтетических для точного прогнозирования

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

## 🏷️ Правила закупок и доставки

### 📦 Линзы (коды 30хххх, 6хххх, 3хххх)
- **Производство:** 45 дней
- **Доставка отдельно:** 12 дней
- **Доставка с растворами:** 0 дней (себестоимость = 0)
- **Общий срок:** 57 дней (отдельно) / 82 дня (с растворами)

### 🧪 Растворы (коды 360360, 500500, 120120)
- **Производство:** 45 дней
- **Доставка отдельно:** 37 дней (30-45 дней)
- **Доставка с линзами:** 37 дней
- **Общий срок:** 82 дня

### 💰 Оптимизация доставки
- **Себестоимость доставки линз = 0** при объединении с растворами
- **Экономия:** до 36 дней в месяц
- **Стратегия:** Растворы заказываются на 25 дней раньше линз

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

# Проверка статуса моделей
curl -s http://localhost:8001/models/status
```

### 5. Переход на реальные данные

Для использования реальных данных из MoySklad вместо синтетических:

```bash
# Обучение моделей на реальных данных
python3 train_real_models.py

# Обновление API (уже выполнено)
python3 update_api_for_real_models.py

# Перезапуск системы
./restart_system.sh
```

Подробная инструкция: [QUICK_REAL_DATA_SETUP.md](QUICK_REAL_DATA_SETUP.md)

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
  "models_used": ["linear_regression", "random_forest"],
  "product_info": {
    "type": "monthly_lenses_6",
    "description": "Месячные линзы по 6 шт",
    "min_order": 5000,
    "multiple": 50,
    "production_days": 45,
    "delivery_days": 12,
    "total_lead_time": 57,
    "safety_stock_days": 15,
    "category": "lenses",
    "can_combine_delivery": true
  }
}
```

### Оптимизация доставки

```bash
# POST /delivery/optimize
curl -X POST "http://localhost:8001/delivery/optimize"
```

**Ответ:**
```json
{
  "status": "success",
  "optimization_result": {
    "can_combine_delivery": true,
    "lenses_count": 3,
    "solutions_count": 2,
    "delivery_savings_days": 36,
    "recommended_action": "combine_delivery",
    "optimal_order_dates": {
      "lenses_order_date": "2024-01-15",
      "solutions_order_date": "2024-01-10",
      "combined_delivery_date": "2024-03-15"
    }
  }
}
```

### Правила доставки

```bash
# GET /delivery/rules
curl http://localhost:8001/delivery/rules
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
3. **Анализирует оптимизацию доставки** для объединения поставок
4. **Создает заказы** для товаров с низкими остатками
5. **Генерирует отчеты** о результатах

### Отчеты

- **Детальный отчет:** `/app/data/daily_report_YYYYMMDD.json`
- **Сводка:** `/app/data/daily_summary.json`
- **Отчет по доставке:** `/app/data/delivery_optimization_report.txt`
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

## 🚚 Оптимизация доставки

### Алгоритм оптимизации:
1. **Анализ товаров** с низкими остатками
2. **Разделение на категории** (линзы/растворы)
3. **Расчет экономии** при объединении поставок
4. **Определение оптимальных дат** заказа
5. **Генерация рекомендаций** по доставке

### Экономический эффект:
- **Себестоимость доставки линз = 0** при объединении
- **Экономия:** до 36 дней в месяц
- **Оптимизация:** до 60% снижения затрат на доставку

## 🛠 Разработка

### Структура проекта

```
services/moysklad-service/
├── app/
│   ├── api_ml.py                    # FastAPI для прогнозирования
│   ├── delivery_optimizer.py        # Оптимизатор доставки
│   ├── product_rules.py             # Правила закупок с доставкой
│   ├── daily_automation.py          # Ежедневная автоматизация
│   ├── train_forecast_models.py     # Обучение ML-моделей
│   ├── export_demands.py            # Экспорт данных из МойСклад
│   └── core/
│       └── config.py                # Настройки
├── data/                            # Данные и модели
├── Dockerfile                       # Docker образ
└── requirements.txt                 # Зависимости
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
- Экономия на доставке

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

### Проблемы с оптимизацией доставки

```bash
# Проверка оптимизатора
docker-compose run --rm -w /app moysklad-service python app/delivery_optimizer.py
```

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи: `docker-compose logs`
2. Убедитесь в корректности настроек в `.env`
3. Проверьте доступность API МойСклад
4. Обратитесь к документации МойСклад API

## 📄 Лицензия

MIT License
