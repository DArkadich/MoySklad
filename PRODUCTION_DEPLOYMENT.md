# 🚀 Деплой на проде - Финальная инструкция

## 📋 Что нужно сделать на проде

### **1. Подготовка сервера**
```bash
# Установить Docker и Docker Compose (если не установлены)
sudo apt update
sudo apt install docker.io docker-compose git

# Создать пользователя для приложения
sudo useradd -m -s /bin/bash moysklad
sudo usermod -aG docker moysklad
```

### **2. Клонирование репозитория**
```bash
# Переключиться на пользователя
sudo su - moysklad

# Клонировать репозиторий
git clone https://github.com/DArkadich/MoySklad.git
cd MoySklad

# Проверить что исторические данные есть
ls -la data/
```

### **3. Настройка переменных окружения**
```bash
# Скопировать пример конфигурации
cp env.example .env

# Отредактировать файл с токеном
nano .env

# Указать реальный токен МойСклад:
# MOYSKLAD_API_TOKEN=your_real_token_here
```

### **4. Запуск системы**
```bash
# Сделать скрипт исполняемым
chmod +x start_system_optimized.sh

# Запустить систему
./start_system_optimized.sh
```

### **5. Копирование исторических данных в контейнер**
```bash
# Дождаться запуска контейнеров
docker ps

# Скопировать исторические данные
docker cp data/production_stock_data.csv forecast-api:/app/data/

# Проверить что данные скопировались
docker exec -it forecast-api ls -la /app/data/
```

### **6. Обучение ML моделей**
```bash
# Скопировать скрипт обучения
docker cp train_models_in_container.py forecast-api:/app/

# Запустить обучение на реальных данных
docker exec -it forecast-api python3 train_models_in_container.py
```

### **7. Проверка работы системы**
```bash
# Проверить API
curl http://localhost:8001/health

# Проверить статус моделей
curl http://localhost:8001/models/status

# Тестирование прогнозирования
curl -X POST http://localhost:8001/forecast \
  -H "Content-Type: application/json" \
  -d '{"product_code": "12345", "forecast_days": 30}'
```

## 🔧 Устранение неполадок

### **Если контейнеры не запускаются:**
```bash
# Проверить логи
docker-compose logs

# Перезапустить
docker-compose down
docker-compose up -d
```

### **Если нет исторических данных:**
```bash
# Проверить наличие файлов
ls -la data/production_stock_data.csv

# Если файлов нет, скопировать из репозитория
git checkout data/production_stock_data.csv
```

### **Если обучение не работает:**
```bash
# Проверить права доступа
docker exec -it forecast-api ls -la /app/data/

# Создать папки если нужно
docker exec -it forecast-api mkdir -p /app/data/models
```

## 📊 Мониторинг

### **Проверка статуса:**
```bash
# Статус контейнеров
docker-compose ps

# Логи API
docker logs forecast-api

# Логи автоматизации
docker logs automation-cron
```

### **Автоматическое дообучение:**
- Система автоматически дообучает модели в 6:00
- Логи сохраняются в `./data/`
- Отчеты: `./data/daily_report_YYYYMMDD.json`

## ✅ Критерии успешного деплоя

1. **API доступен** - `curl http://localhost:8001/health` возвращает 200
2. **Модели загружены** - `/models/status` показывает количество моделей
3. **Прогнозирование работает** - `/forecast` возвращает прогнозы
4. **Автоматизация настроена** - логи показывают ежедневные задачи

## 🎯 Результат

После успешного деплоя у вас будет:
- ✅ ML API с реальными моделями
- ✅ Автоматическое прогнозирование спроса
- ✅ Ежедневное дообучение моделей
- ✅ Интеграция с МойСклад

**Система готова к продуктивному использованию!** 🚀 