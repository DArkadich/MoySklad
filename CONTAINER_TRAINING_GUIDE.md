# Обучение моделей в Docker контейнере

## 🐳 Правильный подход

Поскольку система работает в Docker контейнерах, обучение моделей должно происходить внутри контейнера, а не на хост-машине.

## 🚀 Быстрый старт

### 1. Запуск обучения моделей в контейнере

```bash
# Запуск обучения моделей внутри Docker контейнера
./train_models_in_container.sh
```

Этот скрипт:
- Проверяет, запущены ли контейнеры
- Запускает обучение моделей внутри контейнера `moysklad-service`
- Перезапускает сервис для загрузки новых моделей
- Проверяет статус моделей

### 2. Ручной запуск (если нужно)

```bash
# Проверка запущенных контейнеров
docker ps

# Запуск обучения внутри контейнера
docker exec -it moysklad-service python3 /app/train_models_in_container.py

# Перезапуск сервиса
docker restart moysklad-service
```

## 📁 Структура файлов

### В контейнере:
- `/app/train_models_in_container.py` - скрипт обучения
- `/app/data/real_models/` - директория для сохранения моделей

### На хост-машине:
- `train_models_in_container.sh` - скрипт запуска обучения
- `train_models_in_container.py` - копия скрипта обучения

## 🔧 Настройка

### Переменные окружения в контейнере:
```bash
MOYSKLAD_API_TOKEN=your_api_token_here
MOYSKLAD_API_URL=https://api.moysklad.ru/api/remap/1.2
```

### Проверка переменных в контейнере:
```bash
docker exec -it moysklad-service env | grep MOYSKLAD
```

## 📊 Мониторинг

### Логи обучения:
```bash
docker logs moysklad-service | grep "обучение"
```

### Статус моделей:
```bash
curl -s http://localhost:8001/models/status
```

### Проверка файлов моделей в контейнере:
```bash
docker exec -it moysklad-service ls -la /app/data/real_models/
```

## 🆘 Устранение неполадок

### Проблема: "Контейнер не найден"
**Решение**: Запустите систему
```bash
./start_system.sh
```

### Проблема: "Ошибка API MoySklad"
**Решение**: Проверьте токен в контейнере
```bash
docker exec -it moysklad-service env | grep MOYSKLAD_API_TOKEN
```

### Проблема: "Нет прав на запись"
**Решение**: Проверьте права доступа в контейнере
```bash
docker exec -it moysklad-service ls -la /app/data/
```

### Проблема: "Модели не загружаются"
**Решение**: Перезапустите сервис
```bash
docker restart moysklad-service
```

## 📝 Примеры использования

### Обучение моделей для всех товаров:
```bash
./train_models_in_container.sh
```

### Проверка результатов:
```bash
# Статус моделей
curl -s http://localhost:8001/models/status

# Тест прогноза
curl -X POST http://localhost:8001/forecast \
  -H "Content-Type: application/json" \
  -d '{"product_code":"real_product_id","forecast_days":30}'
```

### Просмотр логов:
```bash
docker logs moysklad-service -f
```

## 🎯 Преимущества контейнерного подхода

1. **Изоляция**: Обучение происходит в изолированной среде
2. **Консистентность**: Одинаковые условия на всех машинах
3. **Зависимости**: Все необходимые библиотеки уже установлены
4. **Масштабируемость**: Легко переносить между серверами
5. **Мониторинг**: Централизованное логирование

## 🔄 Автоматизация

Для автоматического обучения можно настроить cron:

```bash
# Добавить в crontab
0 2 * * * /path/to/MoySklad/train_models_in_container.sh >> /var/log/model_training.log 2>&1
```

Это будет запускать обучение моделей каждый день в 2:00 утра.

---

**Готово!** Теперь обучение моделей происходит правильно внутри Docker контейнера. 🎉 