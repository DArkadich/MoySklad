# 🚀 Инструкции по деплою системы

## 📋 Предварительные требования

### **На сервере должны быть установлены:**
- Docker
- Docker Compose
- Git

## 🔄 Шаги деплоя

### **1. Клонирование репозитория**
```bash
git clone https://github.com/DArkadich/MoySklad.git
cd MoySklad
```

### **2. Настройка переменных окружения**
```bash
cp env.example .env
nano .env
```

**В файле .env укажите:**
```env
MOYSKLAD_API_TOKEN=your_actual_token_here
```

### **3. Запуск системы**
```bash
chmod +x start_system_optimized.sh
./start_system_optimized.sh
```

### **4. Первоначальное обучение ML моделей**
```bash
# Копируем скрипт обучения в контейнер
docker cp train_models_in_container.py forecast-api:/app/

# Копируем исторические данные в контейнер
docker cp data/production_stock_data.csv forecast-api:/app/data/

# Запускаем обучение в контейнере
docker exec -it forecast-api python3 train_models_in_container.py
```

### **5. Проверка работы системы**
```bash
# Проверка API
curl http://localhost:8001/health

# Проверка статуса моделей
curl http://localhost:8001/models/status

# Тестирование прогнозирования
curl -X POST http://localhost:8001/forecast \
  -H "Content-Type: application/json" \
  -d '{"product_code": "12345", "forecast_days": 30}'
```

## 📊 Мониторинг системы

### **Проверка логов:**
```bash
# Логи API
docker logs forecast-api

# Логи автоматизации
docker logs automation-cron

# Логи всех сервисов
docker-compose logs
```

### **Проверка статуса сервисов:**
```bash
docker-compose ps
```

## 🔧 Управление системой

### **Остановка системы:**
```bash
docker-compose down
```

### **Перезапуск системы:**
```bash
docker-compose restart
```

### **Обновление системы:**
```bash
git pull origin main
docker-compose down
docker-compose up -d --build
```

## 📈 Ежедневная работа

### **Автоматическое дообучение:**
- Система автоматически дообучает модели свежими данными в 6:00
- Логи сохраняются в `./data/`
- Отчеты доступны в `./data/daily_report_YYYYMMDD.json`

### **Ручное дообучение:**
```bash
docker exec -it forecast-api python3 -c "
from app.incremental_learning import IncrementalModelTrainer
import asyncio
trainer = IncrementalModelTrainer()
asyncio.run(trainer.incremental_train_all_models())
"
```

## 🐛 Устранение неполадок

### **Если API недоступен:**
```bash
# Проверка статуса контейнеров
docker-compose ps

# Перезапуск API
docker-compose restart forecast-api

# Проверка логов
docker logs forecast-api
```

### **Если модели не загружаются:**
```bash
# Проверка наличия моделей
docker exec -it forecast-api ls -la /app/data/models/

# Проверка наличия исторических данных
docker exec -it forecast-api ls -la /app/data/production_stock_data.csv

# Копируем исторические данные если их нет
docker cp data/production_stock_data.csv forecast-api:/app/data/

# Перезапуск первоначального обучения
docker exec -it forecast-api python3 train_models_in_container.py
```

### **Если нет исторических данных:**
```bash
# Исторические данные уже включены в репозиторий
# Копируем их в контейнер:
docker cp data/production_stock_data.csv forecast-api:/app/data/

# Проверяем что данные скопировались:
docker exec -it forecast-api ls -la /app/data/production_stock_data.csv
```

## 📊 Структура файлов после деплоя

```
MoySklad/
├── .env                          # Переменные окружения
├── docker-compose.yml            # Конфигурация Docker
├── start_system_optimized.sh     # Скрипт запуска
├── train_initial_models.py       # Скрипт первоначального обучения
├── test_api_ml.py               # Тесты API
├── data/                        # Данные и модели
│   ├── models/                  # Обученные ML модели
│   ├── stock_history.csv        # Исторические данные об остатках
│   ├── sales_history.csv        # Исторические данные о продажах
│   └── daily_report_*.json      # Ежедневные отчеты
└── services/
    └── moysklad-service/
        └── app/
            ├── api_ml.py        # ML API
            ├── train_historical_models.py  # Обучение на исторических данных
            ├── incremental_learning.py     # Дообучение
            └── daily_automation.py        # Автоматизация
```

## ✅ Проверка успешного деплоя

### **Все должно работать:**
- ✅ API доступен на http://localhost:8001
- ✅ Модели загружены (проверить `/models/status`)
- ✅ Прогнозирование работает (проверить `/forecast`)
- ✅ Автоматизация настроена (проверить логи)

Система готова к продуктивному использованию! 🎯 