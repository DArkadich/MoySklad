#!/usr/bin/env python3
"""
Проверка ML-моделей внутри Docker контейнера
"""

import subprocess
import json
import requests
from datetime import datetime
from typing import Dict, Any

def run_docker_command(command: list) -> tuple:
    """Выполнение команды в Docker контейнере"""
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Timeout expired"
    except Exception as e:
        return False, "", str(e)

def check_docker_containers():
    """Проверка Docker контейнеров"""
    print("🔍 Проверка Docker контейнеров...")
    
    # Проверяем запущенные контейнеры
    success, output, error = run_docker_command(['docker', 'ps'])
    if not success:
        print(f"❌ Ошибка проверки контейнеров: {error}")
        return False
    
    # Ищем ML-сервис
    ml_service_running = 'ml-service' in output
    if ml_service_running:
        print("✅ ML-сервис запущен в Docker")
        return True
    else:
        print("❌ ML-сервис не найден в запущенных контейнерах")
        print("   Запущенные контейнеры:")
        for line in output.strip().split('\n')[1:]:  # Пропускаем заголовок
            if line.strip():
                print(f"     {line}")
        return False

def check_ml_service_health():
    """Проверка здоровья ML-сервиса через Docker"""
    print("\n🏥 Проверка здоровья ML-сервиса...")
    
    # Проверяем через curl внутри контейнера
    success, output, error = run_docker_command([
        'docker', 'exec', 'ml-service', 'curl', '-s', 'http://localhost:8002/health'
    ])
    
    if success and output:
        try:
            health_data = json.loads(output)
            print("✅ ML-сервис здоров")
            print(f"   Загружено моделей: {health_data.get('models_loaded', 0)}")
            return True, health_data
        except json.JSONDecodeError:
            print(f"❌ Неверный ответ от сервиса: {output}")
            return False, None
    else:
        print(f"❌ ML-сервис недоступен: {error}")
        return False, None

def get_models_status():
    """Получение статуса моделей через Docker"""
    print("\n📊 Получение статуса моделей...")
    
    success, output, error = run_docker_command([
        'docker', 'exec', 'ml-service', 'curl', '-s', 'http://localhost:8002/models/status'
    ])
    
    if success and output:
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            print(f"❌ Неверный ответ от API: {output}")
            return None
    else:
        print(f"❌ Ошибка получения статуса: {error}")
        return None

def check_models_files():
    """Проверка файлов моделей в контейнере"""
    print("\n📁 Проверка файлов моделей в контейнере...")
    
    success, output, error = run_docker_command([
        'docker', 'exec', 'ml-service', 'ls', '-la', '/app/data/models/'
    ])
    
    if success:
        print("✅ Директория моделей найдена")
        lines = output.strip().split('\n')
        model_files = [line for line in lines if line.endswith(('.pkl', '.joblib'))]
        
        if model_files:
            print(f"   Найдено файлов моделей: {len(model_files)}")
            for file_info in model_files[:5]:
                print(f"     {file_info}")
            if len(model_files) > 5:
                print(f"     ... и еще {len(model_files) - 5} файлов")
            return model_files
        else:
            print("   ⚠️ Файлы моделей не найдены")
            return []
    else:
        print(f"❌ Ошибка проверки файлов: {error}")
        return []

def test_forecast_in_container(product_id: str = "30001"):
    """Тестирование прогноза через контейнер"""
    print(f"\n🧪 Тестирование прогноза для {product_id}...")
    
    forecast_request = {
        "product_id": product_id,
        "forecast_days": 30,
        "model_type": None
    }
    
    # Отправляем запрос через curl в контейнере
    success, output, error = run_docker_command([
        'docker', 'exec', 'ml-service', 'curl', '-s', '-X', 'POST',
        'http://localhost:8002/forecast',
        '-H', 'Content-Type: application/json',
        '-d', json.dumps(forecast_request)
    ])
    
    if success and output:
        try:
            forecast_data = json.loads(output)
            print("✅ Прогноз получен")
            print(f"   Дневной спрос: {forecast_data.get('daily_demand', 0):.2f}")
            print(f"   Точность: {forecast_data.get('accuracy', 0):.2%}")
            print(f"   Модель: {forecast_data.get('model_type', 'unknown')}")
            return forecast_data
        except json.JSONDecodeError:
            print(f"❌ Неверный ответ прогноза: {output}")
            return None
    else:
        print(f"❌ Ошибка получения прогноза: {error}")
        return None

def check_ml_logs():
    """Проверка логов ML-сервиса"""
    print("\n📋 Проверка логов ML-сервиса...")
    
    success, output, error = run_docker_command([
        'docker', 'logs', '--tail', '20', 'ml-service'
    ])
    
    if success:
        print("📄 Последние 20 строк логов:")
        for line in output.strip().split('\n'):
            if line.strip():
                print(f"   {line}")
        
        # Проверяем наличие ошибок
        error_lines = [line for line in output.split('\n') if 'error' in line.lower() or 'exception' in line.lower()]
        if error_lines:
            print(f"\n⚠️ Найдено {len(error_lines)} строк с ошибками:")
            for line in error_lines[:5]:
                print(f"   {line}")
    else:
        print(f"❌ Ошибка получения логов: {error}")

def check_container_resources():
    """Проверка ресурсов контейнера"""
    print("\n💾 Проверка ресурсов контейнера...")
    
    success, output, error = run_docker_command([
        'docker', 'stats', 'ml-service', '--no-stream', '--format', 'table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}'
    ])
    
    if success:
        print("📊 Статистика ресурсов:")
        for line in output.strip().split('\n'):
            if line.strip():
                print(f"   {line}")
    else:
        print(f"❌ Ошибка получения статистики: {error}")

def main():
    """Основная функция проверки"""
    
    print("🐳 ПРОВЕРКА ML-МОДЕЛЕЙ В DOCKER КОНТЕЙНЕРЕ")
    print("=" * 60)
    
    # 1. Проверяем Docker контейнеры
    containers_ok = check_docker_containers()
    
    if not containers_ok:
        print("\n💡 РЕКОМЕНДАЦИИ:")
        print("   1. Запустите систему: ./start_system.sh")
        print("   2. Или запустите только ML-сервис: docker-compose up -d ml-service")
        print("   3. Проверьте docker-compose.yml")
        return
    
    # 2. Проверяем здоровье сервиса
    service_healthy, health_data = check_ml_service_health()
    
    if not service_healthy:
        print("\n💡 РЕКОМЕНДАЦИИ:")
        print("   1. Перезапустите ML-сервис: docker restart ml-service")
        print("   2. Проверьте логи: docker logs ml-service")
        print("   3. Проверьте порты: docker port ml-service")
        return
    
    # 3. Получаем статус моделей
    models_status = get_models_status()
    
    if models_status:
        print("\n📊 СТАТУС МОДЕЛЕЙ:")
        print(f"   Всего моделей: {models_status.get('total_models', 0)}")
        print(f"   Средняя точность: {models_status.get('average_accuracy', 0):.2%}")
        
        models_by_type = models_status.get('models_by_type', {})
        if models_by_type:
            print("   Модели по типам:")
            for model_type, count in models_by_type.items():
                print(f"     {model_type}: {count} моделей")
        else:
            print("   ⚠️ Нет загруженных моделей")
    
    # 4. Проверяем файлы моделей
    model_files = check_models_files()
    
    # 5. Проверяем ресурсы
    check_container_resources()
    
    # 6. Проверяем логи
    check_ml_logs()
    
    # 7. Тестируем прогноз
    print("\n🧪 Тестирование прогнозов...")
    test_products = ["30001", "30002", "60001", "360360"]
    
    for product_id in test_products:
        forecast = test_forecast_in_container(product_id)
        if not forecast:
            print(f"   ❌ Прогноз недоступен для {product_id}")
    
    # 8. Сохраняем результаты
    print("\n💾 Сохранение результатов...")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "containers_ok": containers_ok,
        "service_healthy": service_healthy,
        "health_data": health_data,
        "models_status": models_status,
        "model_files": model_files,
        "test_results": {}
    }
    
    # Добавляем результаты тестов
    for product_id in test_products:
        forecast = test_forecast_in_container(product_id)
        results["test_results"][product_id] = forecast
    
    # Сохраняем в файл
    with open('ml_models_docker_status.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    
    print("✅ Результаты сохранены в файл: ml_models_docker_status.json")
    
    # 9. Вывод итогового статуса
    print("\n" + "=" * 60)
    print("📋 ИТОГОВЫЙ СТАТУС:")
    
    if service_healthy and models_status and models_status.get('total_models', 0) > 0:
        print("✅ ML-модели обучены и готовы к использованию")
        print(f"   Загружено моделей: {models_status.get('total_models', 0)}")
        print(f"   Средняя точность: {models_status.get('average_accuracy', 0):.2%}")
    elif service_healthy:
        print("⚠️ ML-сервис работает, но модели не загружены")
        print("   Необходимо обучить модели")
    else:
        print("❌ ML-сервис недоступен")
        print("   Проверьте, что сервис запущен")

if __name__ == "__main__":
    main() 