#!/usr/bin/env python3
"""
Диагностика проблемы загрузки ML-моделей
"""

import os
import pickle
import sys
import traceback
from datetime import datetime

def check_model_file():
    """Проверка файла модели"""
    print("🔍 ПРОВЕРКА ФАЙЛА МОДЕЛИ")
    print("=" * 40)
    
    model_path = "data/universal_forecast_models.pkl"
    
    if not os.path.exists(model_path):
        print(f"❌ Файл модели не найден: {model_path}")
        return False
    
    print(f"✅ Файл модели найден: {model_path}")
    
    # Проверка размера файла
    size = os.path.getsize(model_path)
    size_mb = size / (1024 * 1024)
    print(f"   Размер: {size_mb:.2f} MB")
    
    return True

def test_model_loading():
    """Тест загрузки модели"""
    print("\n🧪 ТЕСТ ЗАГРУЗКИ МОДЕЛИ")
    print("=" * 40)
    
    model_path = "data/universal_forecast_models.pkl"
    
    try:
        print(f"Попытка загрузки модели из: {model_path}")
        
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        print("✅ Модель успешно загружена!")
        
        # Анализ структуры данных
        print(f"   Тип данных: {type(model_data)}")
        
        if isinstance(model_data, dict):
            print(f"   Ключи: {list(model_data.keys())}")
            
            if 'models' in model_data:
                models = model_data['models']
                print(f"   Количество моделей: {len(models)}")
                
                for i, (product_code, model_info) in enumerate(models.items()):
                    print(f"   Модель {i+1}: {product_code}")
                    if isinstance(model_info, dict):
                        print(f"     Типы: {list(model_info.keys())}")
                    else:
                        print(f"     Тип: {type(model_info)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка загрузки модели: {e}")
        print(f"   Тип ошибки: {type(e).__name__}")
        print("   Полная ошибка:")
        traceback.print_exc()
        return False

def test_numpy_import():
    """Тест импорта numpy"""
    print("\n📦 ТЕСТ ИМПОРТА NUMPY")
    print("=" * 40)
    
    try:
        import numpy as np
        print(f"✅ NumPy импортирован успешно")
        print(f"   Версия: {np.__version__}")
        print(f"   Путь: {np.__file__}")
        return True
    except Exception as e:
        print(f"❌ Ошибка импорта NumPy: {e}")
        return False

def test_sklearn_import():
    """Тест импорта scikit-learn"""
    print("\n🤖 ТЕСТ ИМПОРТА SCIKIT-LEARN")
    print("=" * 40)
    
    try:
        import sklearn
        print(f"✅ Scikit-learn импортирован успешно")
        print(f"   Версия: {sklearn.__version__}")
        print(f"   Путь: {sklearn.__file__}")
        return True
    except Exception as e:
        print(f"❌ Ошибка импорта scikit-learn: {e}")
        return False

def test_pickle_security():
    """Тест безопасности pickle"""
    print("\n🔒 ТЕСТ БЕЗОПАСНОСТИ PICKLE")
    print("=" * 40)
    
    try:
        import pickle
        print(f"✅ Pickle доступен")
        print(f"   Версия: {pickle.format_version}")
        
        # Проверка предупреждений
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Попытка загрузки модели
            model_path = "data/universal_forecast_models.pkl"
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
            
            if w:
                print("⚠️  Предупреждения при загрузке:")
                for warning in w:
                    print(f"   {warning.message}")
            else:
                print("✅ Загрузка без предупреждений")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка теста pickle: {e}")
        return False

def main():
    """Основная функция диагностики"""
    print("🔧 ДИАГНОСТИКА ПРОБЛЕМЫ ЗАГРУЗКИ МОДЕЛЕЙ")
    print("=" * 50)
    print(f"📅 Время: {datetime.now()}")
    print()
    
    # Проверки
    checks = [
        ("Файл модели", check_model_file),
        ("Импорт NumPy", test_numpy_import),
        ("Импорт Scikit-learn", test_sklearn_import),
        ("Безопасность Pickle", test_pickle_security),
        ("Загрузка модели", test_model_loading),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n{'='*20} {name} {'='*20}")
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Ошибка в проверке {name}: {e}")
            results.append((name, False))
    
    # Итоговая оценка
    print("\n" + "="*50)
    print("📊 ИТОГОВАЯ ОЦЕНКА")
    print("="*50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    print(f"\nРезультат: {passed}/{total} проверок пройдено")
    
    if passed == total:
        print("🎉 Все проверки пройдены! Модели должны загружаться.")
    elif passed >= total - 1:
        print("⚠️  Большинство проверок пройдено. Возможны незначительные проблемы.")
    else:
        print("❌ Много проблем. Требуется исправление.")
    
    print(f"\n📅 Диагностика завершена: {datetime.now()}")

if __name__ == "__main__":
    main() 