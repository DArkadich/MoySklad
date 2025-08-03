#!/usr/bin/env python3
"""
Анализ структуры данных модели
"""

import pickle
import os
from datetime import datetime

def analyze_model_structure():
    """Анализ структуры данных модели"""
    
    print("🔍 АНАЛИЗ СТРУКТУРЫ ДАННЫХ МОДЕЛИ")
    print("=" * 50)
    print(f"📅 Время: {datetime.now()}")
    print()
    
    model_path = "data/universal_forecast_models.pkl"
    
    if not os.path.exists(model_path):
        print(f"❌ Файл модели не найден: {model_path}")
        return
    
    try:
        print(f"📁 Загрузка модели из: {model_path}")
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        print(f"✅ Модель загружена")
        print(f"   Тип данных: {type(model_data)}")
        
        if isinstance(model_data, dict):
            print(f"   Ключи: {list(model_data.keys())}")
            
            for key, value in model_data.items():
                print(f"\n🔍 Анализ ключа: {key}")
                print(f"   Тип значения: {type(value)}")
                
                if isinstance(value, dict):
                    print(f"   Подключи: {list(value.keys())}")
                    
                    for sub_key, sub_value in value.items():
                        print(f"     {sub_key}: {type(sub_value)}")
                        if hasattr(sub_value, 'predict'):
                            print(f"       ✅ Имеет метод predict (модель)")
                        elif hasattr(sub_value, 'fit'):
                            print(f"       ✅ Имеет метод fit (обучаемый объект)")
                        elif isinstance(sub_value, (list, tuple)):
                            print(f"       📊 Размер: {len(sub_value)}")
                        elif isinstance(sub_value, str):
                            print(f"       📝 Строка: {sub_value[:50]}...")
                        elif isinstance(sub_value, (int, float)):
                            print(f"       🔢 Число: {sub_value}")
                
                elif hasattr(value, 'predict'):
                    print(f"   ✅ Прямая модель с методом predict")
                    print(f"     Тип модели: {type(value).__name__}")
                
                elif isinstance(value, (list, tuple)):
                    print(f"   📊 Список/кортеж размером: {len(value)}")
                    if len(value) > 0:
                        print(f"     Первый элемент: {type(value[0])}")
                
                elif isinstance(value, str):
                    print(f"   📝 Строка: {value[:100]}...")
                
                else:
                    print(f"   ❓ Неизвестный тип: {type(value)}")
        
        # Поиск моделей
        print(f"\n🤖 ПОИСК МОДЕЛЕЙ В ДАННЫХ")
        print("=" * 30)
        
        models_found = []
        
        def find_models(data, path=""):
            if hasattr(data, 'predict'):
                models_found.append((path, type(data).__name__))
                return
            
            if isinstance(data, dict):
                for key, value in data.items():
                    find_models(value, f"{path}.{key}" if path else key)
            elif isinstance(data, (list, tuple)):
                for i, item in enumerate(data):
                    find_models(item, f"{path}[{i}]")
        
        find_models(model_data)
        
        if models_found:
            print(f"✅ Найдено моделей: {len(models_found)}")
            for path, model_type in models_found:
                print(f"   • {path}: {model_type}")
        else:
            print("❌ Модели не найдены")
        
        # Рекомендации
        print(f"\n💡 РЕКОМЕНДАЦИИ")
        print("=" * 20)
        
        if models_found:
            print("✅ Модели найдены в данных")
            print("   • Проверьте код загрузки на соответствие структуре")
            print("   • Убедитесь, что пути к моделям правильные")
        else:
            print("❌ Модели не найдены в данных")
            print("   • Проверьте, что файл содержит обученные модели")
            print("   • Возможно, нужно переобучить модели")
        
        print(f"\n📅 Анализ завершен: {datetime.now()}")
        
    except Exception as e:
        print(f"❌ Ошибка анализа: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_model_structure() 