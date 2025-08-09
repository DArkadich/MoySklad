# 🚀 Быстрая проверка ML моделей в продакшене

## 📋 Что проверить

### 1. **Автоматическая проверка (рекомендуется)**
```bash
# Запустить полную проверку
./check_production_ml.sh

# Или Python скрипт
python3 check_production_ml_simple.py
```

### 2. **Ручная проверка по шагам**

#### Шаг 1: Статус контейнеров
```bash
docker ps | grep -E "(ml-service|forecast-api|moysklad-service)"
```

#### Шаг 2: Проверка здоровья сервисов
```bash
# Проверка forecast-api
curl -s http://localhost:8001/health

# Проверка ml-service
curl -s http://localhost:8002/health

# Проверка moysklad-service
curl -s http://localhost:8000/health
```

#### Шаг 3: Статус моделей
```bash
curl -s http://localhost:8001/models/status
```

#### Шаг 4: Проверка файлов в контейнере
```bash
# Вход в контейнер
docker exec -it forecast-api bash

# Проверка файлов
ls -la /app/data/
find /app/data/ -name "*.pkl" -o -name "*.joblib"

# Выход
exit
```

#### Шаг 5: Тест прогнозирования
```bash
curl -X POST http://localhost:8001/forecast \
  -H "Content-Type: application/json" \
  -d '{"product_code":"30001","forecast_days":30}'
```

## ✅ Что должно быть

### **ML модели обучены:**
- `models_loaded > 0` в health endpoint
- Файлы `.pkl` или `.joblib` в `/app/data/`
- API прогнозирования возвращает прогнозы

### **ML сервисы работают:**
- Контейнеры запущены и здоровы
- Health endpoints возвращают 200 OK
- Логи без критических ошибок

## ❌ Что делать если модели не обучены

### 1. **Проверить наличие данных**
```bash
docker exec forecast-api ls -la /app/data/
```

### 2. **Запустить обучение**
```bash
docker exec forecast-api python3 train_models_in_container.py
```

### 3. **Проверить логи обучения**
```bash
docker-compose logs forecast-api
```

## 🔧 Диагностика проблем

### **Контейнеры не запускаются:**
```bash
docker-compose logs
docker-compose down && docker-compose up -d
```

### **Модели не загружаются:**
```bash
# Проверить логи
docker-compose logs forecast-api

# Проверить файлы
docker exec forecast-api ls -la /app/data/

# Перезапустить сервис
docker-compose restart forecast-api
```

### **API недоступен:**
```bash
# Проверить порты
netstat -tlnp | grep :8001

# Проверить логи
docker-compose logs forecast-api
```

## 📊 Ожидаемые результаты

### **Успешная проверка:**
```
✅ ML-МОДЕЛИ ОБУЧЕНЫ И ГОТОВЫ К ИСПОЛЬЗОВАНИЮ
   • Загружено моделей: X
   • API прогнозирования работает
```

### **Модели не загружены:**
```
⚠️ ML-СЕРВИСЫ РАБОТАЮТ, НО МОДЕЛИ НЕ ЗАГРУЖЕНЫ
   • Необходимо обучить модели
```

### **Сервисы не работают:**
```
❌ ML-СЕРВИСЫ НЕ РАБОТАЮТ
   • Проверьте статус контейнеров
```

## 🚨 Критические проблемы

### **Если ничего не работает:**
1. Проверить Docker: `docker --version`
2. Проверить docker-compose: `docker-compose --version`
3. Перезапустить систему: `./restart_system_fixed.sh`
4. Проверить логи: `docker-compose logs`

### **Если модели не обучаются:**
1. Проверить наличие данных: `ls -la data/`
2. Проверить права доступа к файлам
3. Проверить свободное место на диске
4. Проверить логи обучения

## 💡 Полезные команды

```bash
# Быстрая проверка
./check_production_ml.sh

# Детальная проверка
python3 check_production_ml_simple.py

# Проверка логов в реальном времени
docker-compose logs -f forecast-api

# Перезапуск ML сервиса
docker-compose restart forecast-api

# Проверка статуса системы
docker-compose ps
```
