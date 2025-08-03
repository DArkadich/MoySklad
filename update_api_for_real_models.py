#!/usr/bin/env python3
"""
Скрипт для обновления API сервиса для работы с реальными моделями
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_api_ml_service():
    """Обновление API ML сервиса для работы с реальными моделями"""
    
    api_file = "services/moysklad-service/app/api_ml.py"
    
    # Читаем текущий файл
    with open(api_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Заменяем синтетический код товара на динамическое получение
    old_code = 'product_code = "30001"  # Универсальный код для всех продуктов'
    new_code = '''# Получаем реальный product_code из запроса или используем ID товара
product_code = request.product_code if hasattr(request, 'product_code') else product_id'''
    
    content = content.replace(old_code, new_code)
    
    # Заменяем второе вхождение
    old_code2 = 'product_code = "30001"  # Универсальный код'
    new_code2 = '''# Используем реальный product_code
product_code = request.product_code if hasattr(request, 'product_code') else product_id'''
    
    content = content.replace(old_code2, new_code2)
    
    # Добавляем функцию для загрузки реальных моделей
    real_models_function = '''
def load_real_models():
    """Загрузка реальных моделей из data/real_models"""
    real_models = {}
    real_models_dir = "data/real_models"
    
    if not os.path.exists(real_models_dir):
        logger.warning(f"Директория реальных моделей не найдена: {real_models_dir}")
        return real_models
    
    try:
        # Ищем файлы метаданных
        for filename in os.listdir(real_models_dir):
            if filename.endswith('_metadata.json'):
                metadata_path = os.path.join(real_models_dir, filename)
                
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                product_id = metadata.get('product_id')
                if not product_id:
                    continue
                
                # Загружаем модели для этого товара
                product_models = {}
                for model_name, model_path in metadata.get('models', {}).items():
                    if os.path.exists(model_path):
                        with open(model_path, 'rb') as f:
                            model = pickle.load(f)
                        product_models[model_name] = model
                
                if product_models:
                    real_models[product_id] = {
                        'models': product_models,
                        'metadata': metadata
                    }
                    logger.info(f"Загружены реальные модели для товара {product_id}")
        
        logger.info(f"Загружено {len(real_models)} товаров с реальными моделями")
        return real_models
        
    except Exception as e:
        logger.error(f"Ошибка загрузки реальных моделей: {e}")
        return real_models
'''
    
    # Добавляем импорт os и json если их нет
    if 'import os' not in content:
        content = content.replace('import logging', 'import logging\nimport os\nimport json')
    
    # Добавляем функцию загрузки реальных моделей
    if 'def load_real_models():' not in content:
        # Находим место после импортов
        import_end = content.find('logger = logging.getLogger(__name__)')
        if import_end != -1:
            insert_pos = content.find('\n', import_end) + 1
            content = content[:insert_pos] + real_models_function + '\n' + content[insert_pos:]
    
    # Обновляем функцию load_ml_models для использования реальных моделей
    old_load_function = '''def load_ml_models():
    """Загрузка ML моделей"""
    global ml_models, model_metadata, model_scalers
    
    try:
        # Загружаем универсальную модель
        universal_model_path = "data/universal_forecast_models.pkl"
        
        if os.path.exists(universal_model_path):
            with open(universal_model_path, 'rb') as f:
                model_data = pickle.load(f)
            
            logger.info(f"Тип загруженных данных: {type(model_data)}")
            logger.info(f"Ключи в данных: {list(model_data.keys())}")
            
            if isinstance(model_data, dict):
                # Проверяем структуру models
                if 'models' in model_data:
                    models = model_data['models']
                    logger.info(f"Найдено моделей в 'models': {len(models)}")
                    
                    for model_name, model_obj in models.items():
                        if hasattr(model_obj, 'predict'):
                            # Используем model_name как product_code
                            product_code = "30001"  # Универсальный код для всех продуктов
                            ml_models[product_code] = model_obj
                            logger.info(f"Загружена модель {model_name} для товара {product_code}")
                
                # Проверяем структуру results для метаданных
                if 'results' in model_data:
                    results = model_data['results']
                    logger.info(f"Найдено результатов: {len(results) if isinstance(results, dict) else 'не dict'}")
                    
                    if isinstance(results, dict):
                        for model_name, result_info in results.items():
                            if isinstance(result_info, dict):
                                product_code = "30001"  # Универсальный код
                                if product_code in ml_models:
                                    if 'metadata' in result_info:
                                        model_metadata[product_code] = result_info['metadata']
                                    if 'scaler' in result_info:
                                        model_scalers[product_code] = result_info['scaler']
                                    logger.info(f"Добавлены метаданные для модели {model_name}")
                
                # Проверяем features
                if 'features' in model_data:
                    features = model_data['features']
                    logger.info(f"Найдено признаков: {len(features) if isinstance(features, list) else 'не список'}")
            
            logger.info(f"Загружено моделей: {len(ml_models)}")
            
            if len(ml_models) == 0:
                logger.warning("Модели не загружены. Проверьте структуру данных.")
            else:
                logger.info("✅ Модели успешно загружены!")
                
        else:
            logger.warning(f"Файл универсальной модели не найден: {universal_model_path}")
        
    except Exception as e:
        logger.error(f"Ошибка загрузки моделей: {e}")
        import traceback
        logger.error(f"Полная ошибка: {traceback.format_exc()}")'''
    
    new_load_function = '''def load_ml_models():
    """Загрузка ML моделей"""
    global ml_models, model_metadata, model_scalers
    
    try:
        # Сначала пытаемся загрузить реальные модели
        real_models = load_real_models()
        
        if real_models:
            # Загружаем реальные модели
            for product_id, model_info in real_models.items():
                ml_models[product_id] = model_info['models']
                if 'metadata' in model_info:
                    model_metadata[product_id] = model_info['metadata']
            
            logger.info(f"✅ Загружено {len(real_models)} товаров с реальными моделями")
            return
        
        # Если реальных моделей нет, загружаем универсальную модель
        universal_model_path = "data/universal_forecast_models.pkl"
        
        if os.path.exists(universal_model_path):
            with open(universal_model_path, 'rb') as f:
                model_data = pickle.load(f)
            
            logger.info(f"Тип загруженных данных: {type(model_data)}")
            logger.info(f"Ключи в данных: {list(model_data.keys())}")
            
            if isinstance(model_data, dict):
                # Проверяем структуру models
                if 'models' in model_data:
                    models = model_data['models']
                    logger.info(f"Найдено моделей в 'models': {len(models)}")
                    
                    for model_name, model_obj in models.items():
                        if hasattr(model_obj, 'predict'):
                            # Используем model_name как product_code
                            product_code = "30001"  # Универсальный код для всех продуктов
                            ml_models[product_code] = model_obj
                            logger.info(f"Загружена модель {model_name} для товара {product_code}")
                
                # Проверяем структуру results для метаданных
                if 'results' in model_data:
                    results = model_data['results']
                    logger.info(f"Найдено результатов: {len(results) if isinstance(results, dict) else 'не dict'}")
                    
                    if isinstance(results, dict):
                        for model_name, result_info in results.items():
                            if isinstance(result_info, dict):
                                product_code = "30001"  # Универсальный код
                                if product_code in ml_models:
                                    if 'metadata' in result_info:
                                        model_metadata[product_code] = result_info['metadata']
                                    if 'scaler' in result_info:
                                        model_scalers[product_code] = result_info['scaler']
                                    logger.info(f"Добавлены метаданные для модели {model_name}")
                
                # Проверяем features
                if 'features' in model_data:
                    features = model_data['features']
                    logger.info(f"Найдено признаков: {len(features) if isinstance(features, list) else 'не список'}")
            
            logger.info(f"Загружено моделей: {len(ml_models)}")
            
            if len(ml_models) == 0:
                logger.warning("Модели не загружены. Проверьте структуру данных.")
            else:
                logger.info("✅ Модели успешно загружены!")
                
        else:
            logger.warning(f"Файл универсальной модели не найден: {universal_model_path}")
        
    except Exception as e:
        logger.error(f"Ошибка загрузки моделей: {e}")
        import traceback
        logger.error(f"Полная ошибка: {traceback.format_exc()}")'''
    
    content = content.replace(old_load_function, new_load_function)
    
    # Записываем обновленный файл
    with open(api_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info(f"✅ API ML сервис обновлен: {api_file}")

def update_forecast_endpoint():
    """Обновление эндпоинта прогнозирования для работы с реальными товарами"""
    
    api_file = "services/moysklad-service/app/api_ml.py"
    
    # Читаем текущий файл
    with open(api_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Обновляем функцию прогнозирования для использования реальных товаров
    old_forecast_logic = '''# Получаем текущие остатки
current_stock = await get_current_stock(request.product_code)

# Создаем признаки для ML
features = create_ml_features(request.product_code, datetime.now(), current_stock)

# Получаем прогноз
forecast_result = predict_with_ml_model(request.product_code, features)'''
    
    new_forecast_logic = '''# Получаем текущие остатки
current_stock = await get_current_stock(request.product_code)

# Проверяем, есть ли реальные модели для этого товара
if request.product_code in ml_models:
    # Используем реальные модели
    features = create_ml_features(request.product_code, datetime.now(), current_stock)
    forecast_result = predict_with_ml_model(request.product_code, features)
    logger.info(f"Использованы реальные модели для товара {request.product_code}")
else:
    # Используем универсальную модель или fallback
    features = create_ml_features(request.product_code, datetime.now(), current_stock)
    forecast_result = predict_with_ml_model(request.product_code, features)
    logger.info(f"Использована универсальная модель для товара {request.product_code}")'''
    
    content = content.replace(old_forecast_logic, new_forecast_logic)
    
    # Записываем обновленный файл
    with open(api_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info(f"✅ Эндпоинт прогнозирования обновлен")

def create_test_script():
    """Создание скрипта для тестирования реальных моделей"""
    
    test_script = '''#!/usr/bin/env python3
"""
Скрипт для тестирования реальных моделей
"""

import asyncio
import httpx
import json
from datetime import datetime

async def test_real_models():
    """Тестирование реальных моделей"""
    
    # Получаем список товаров из MoySklad
    async with httpx.AsyncClient() as client:
        # Здесь нужно будет добавить реальный API токен
        headers = {
            "Authorization": "Bearer YOUR_API_TOKEN",
            "Content-Type": "application/json"
        }
        
        response = await client.get(
            "https://api.moysklad.ru/api/remap/1.2/entity/product",
            headers=headers,
            timeout=30.0
        )
        
        if response.status_code == 200:
            products = response.json().get("rows", [])
            print(f"Найдено {len(products)} товаров")
            
            # Тестируем первые 3 товара
            for product in products[:3]:
                product_id = product['id']
                product_name = product.get('name', 'Неизвестный товар')
                product_code = product.get('code', '')
                
                print(f"\\n📦 Тестируем товар: {product_name}")
                print(f"   ID: {product_id}")
                print(f"   Код: {product_code}")
                
                # Тестируем прогноз
                forecast_data = {
                    "product_code": product_id,
                    "forecast_days": 30,
                    "current_stock": 100.0
                }
                
                try:
                    forecast_response = await client.post(
                        "http://localhost:8001/forecast",
                        json=forecast_data,
                        timeout=30.0
                    )
                    
                    if forecast_response.status_code == 200:
                        forecast_result = forecast_response.json()
                        print(f"   ✅ Прогноз получен:")
                        print(f"      Потребление: {forecast_result.get('forecast_consumption', 0)}")
                        print(f"      Рекомендуемый заказ: {forecast_result.get('recommended_order', 0)}")
                        print(f"      Дней до OoS: {forecast_result.get('days_until_oos', 0)}")
                    else:
                        print(f"   ❌ Ошибка прогноза: {forecast_response.status_code}")
                        
                except Exception as e:
                    print(f"   ❌ Ошибка тестирования: {e}")
        else:
            print(f"❌ Ошибка получения товаров: {response.status_code}")

if __name__ == "__main__":
    asyncio.run(test_real_models())
'''
    
    with open('test_real_models.py', 'w', encoding='utf-8') as f:
        f.write(test_script)
    
    logger.info("✅ Создан скрипт тестирования реальных моделей: test_real_models.py")

def main():
    """Основная функция"""
    logger.info("🚀 Обновление API для работы с реальными моделями")
    
    try:
        # Обновляем API ML сервис
        update_api_ml_service()
        
        # Обновляем эндпоинт прогнозирования
        update_forecast_endpoint()
        
        # Создаем скрипт тестирования
        create_test_script()
        
        logger.info("🎉 API успешно обновлен для работы с реальными моделями!")
        logger.info("📝 Следующие шаги:")
        logger.info("   1. Запустите train_real_models.py для обучения моделей на реальных данных")
        logger.info("   2. Перезапустите сервисы")
        logger.info("   3. Запустите test_real_models.py для тестирования")
        
    except Exception as e:
        logger.error(f"Ошибка обновления API: {e}")

if __name__ == "__main__":
    main() 