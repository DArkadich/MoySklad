# Руководство по проверке ML-моделей в продакшн-контейнере

## 🚀 Быстрая проверка

### 1. Автоматическая проверка
```bash
# Полная проверка ML-моделей в продакшене
./check_ml_production.sh
```

### 2. Проверка через Docker
```bash
# Проверка статуса контейнеров
docker ps | grep -E "(ml-service|forecast-api)"

# Проверка здоровья ML-сервиса
curl -s http://localhost:8001/health

# Проверка файлов моделей в контейнере
docker exec forecast-api ls -la /app/data/
```

## 🔍 Детальная проверка

### 1. Проверка контейнеров
```bash
# Все запущенные контейнеры
docker ps

# Контейнеры с ML-сервисами
docker ps | grep -E "(ml-service|forecast-api|moysklad-service)"

# Статус конкретного контейнера
docker ps | grep forecast-api
```

### 2. Проверка здоровья сервиса
```bash
# Проверка через curl
curl -s http://localhost:8001/health | jq .

# Проверка через Docker
docker exec forecast-api curl -s http://localhost:8000/health

# Проверка всех портов
curl -s http://localhost:8000/health  # moysklad-service
curl -s http://localhost:8001/health  # forecast-api
curl -s http://localhost:8002/health  # ml-service (если есть)
```

### 3. Проверка файлов моделей
```bash
# Вход в контейнер
docker exec -it forecast-api bash

# Проверка директории данных
ls -la /app/data/

# Поиск файлов моделей
find /app/data/ -name "*.pkl" -o -name "*.joblib"

# Проверка CSV файлов
find /app/data/ -name "*.csv"

# Выход из контейнера
exit
```

### 4. Тестирование API
```bash
# Тест прогнозирования
curl -X POST http://localhost:8001/forecast \
  -H "Content-Type: application/json" \
  -d '{"product_id":"30001","forecast_days":30}'

# Тест статуса моделей
curl -s http://localhost:8001/models/status

# Тест обучения моделей
curl -X POST http://localhost:8001/retrain-all
```

## 📊 Проверка логов

### 1. Логи ML-сервисов
```bash
# Логи forecast-api
docker-compose logs forecast-api

# Логи moysklad-service
docker-compose logs moysklad-service

# Логи в реальном времени
docker-compose logs -f forecast-api

# Последние 20 строк
docker-compose logs --tail=20 forecast-api
```

### 2. Логи с фильтрацией
```bash
# Логи с ошибками
docker-compose logs forecast-api | grep -i error

# Логи с предупреждениями
docker-compose logs forecast-api | grep -i warning

# Логи загрузки моделей
docker-compose logs forecast-api | grep -i model
```

## 🔧 Диагностика проблем

### 1. Проблема: Сервис не отвечает
```bash
# Проверка статуса контейнера
docker ps | grep forecast-api

# Перезапуск контейнера
docker-compose restart forecast-api

# Проверка ресурсов
docker stats forecast-api
```

### 2. Проблема: Модели не загружены
```bash
# Проверка файлов в контейнере
docker exec forecast-api ls -la /app/data/

# Проверка объема данных
docker exec forecast-api du -sh /app/data/

# Принудительное обучение моделей
curl -X POST http://localhost:8001/retrain-all
```

### 3. Проблема: API недоступен
```bash
# Проверка портов
netstat -tlnp | grep 8001

# Проверка сети Docker
docker network ls
docker network inspect moysklad_moysklad-network

# Перезапуск всей системы
./restart_system_fixed.sh
```

## 📈 Мониторинг производительности

### 1. Проверка ресурсов
```bash
# Использование ресурсов контейнеров
docker stats

# Использование диска
docker system df

# Использование памяти
docker stats --no-stream
```

### 2. Проверка метрик
```bash
# Метрики производительности моделей
curl -s http://localhost:8001/models/performance

# Статистика API
curl -s http://localhost:8001/stats
```

## 🛠️ Полезные команды

### 1. Быстрые проверки
```bash
# Статус системы
docker-compose ps

# Здоровье всех сервисов
for port in 8000 8001 8002; do
  echo "Порт $port: $(curl -s http://localhost:$port/health 2>/dev/null || echo 'недоступен')"
done

# Проверка всех файлов моделей
docker exec forecast-api find /app/data/ -type f -name "*.pkl" -exec ls -lh {} \;
```

### 2. Отладка
```bash
# Вход в контейнер для отладки
docker exec -it forecast-api bash

# Проверка процессов в контейнере
docker exec forecast-api ps aux

# Проверка переменных окружения
docker exec forecast-api env | grep -E "(MODEL|DATA|API)"
```

## 📋 Чек-лист проверки

- [ ] Контейнеры запущены
- [ ] Сервис отвечает на health check
- [ ] Файлы моделей присутствуют
- [ ] API прогнозирования работает
- [ ] Логи без критических ошибок
- [ ] Ресурсы в норме
- [ ] Модели загружены и готовы

## 🚨 Экстренные меры

### 1. Полная перезагрузка
```bash
# Остановка всех контейнеров
docker-compose down

# Очистка ресурсов
docker system prune -f

# Перезапуск с исправлениями
./restart_system_fixed.sh
```

### 2. Восстановление моделей
```bash
# Копирование моделей из резервной копии
cp -r data_backup/* data/

# Перезапуск сервисов
docker-compose restart forecast-api moysklad-service
```

### 3. Проверка после восстановления
```bash
# Полная проверка
./check_ml_production.sh

# Тест прогнозирования
curl -X POST http://localhost:8001/forecast \
  -H "Content-Type: application/json" \
  -d '{"product_id":"30001","forecast_days":30}'
``` 