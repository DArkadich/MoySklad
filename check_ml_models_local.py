#!/usr/bin/env python3
"""
Проверка ML моделей в локальной среде
"""

import os
import pickle
import pandas as pd
import numpy as np
from datetime import datetime
import json

def check_model_files():
    """Проверка файлов моделей"""
    print("🔍 ПРОВЕРКА ФАЙЛОВ ML-МОДЕЛЕЙ")
    print("=" * 50)
    
    # Проверяем основные директории
    data_dirs = [
        "data/",
        "services/moysklad-service/data/"
    ]
    
    model_files = []
    csv_files = []
    
    for data_dir in data_dirs:
        if os.path.exists(data_dir):
            print(f"\n📁 Директория: {data_dir}")
            
            # Ищем файлы моделей
            for filename in os.listdir(data_dir):
                filepath = os.path.join(data_dir, filename)
                if filename.endswith('.pkl') or filename.endswith('.joblib'):
                    model_files.append(filepath)
                    print(f"   ✅ Модель: {filename}")
                elif filename.endswith('.csv'):
                    csv_files.append(filepath)
                    print(f"   📊 Данные: {filename}")
    
    return model_files, csv_files

def load_and_test_models(model_files):
    """Загрузка и тестирование моделей"""
    print(f"\n🤖 ТЕСТИРОВАНИЕ МОДЕЛЕЙ")
    print("=" * 50)
    
    models_info = []
    
    for model_file in model_files:
        try:
            print(f"\n📦 Загрузка модели: {os.path.basename(model_file)}")
            
            with open(model_file, 'rb') as f:
                model_data = pickle.load(f)
            
            print(f"   Тип данных: {type(model_data)}")
            
            if isinstance(model_data, dict):
                print(f"   Ключи: {list(model_data.keys())}")
                
                # Проверяем содержимое
                for key, value in model_data.items():
                    if hasattr(value, 'predict'):
                        print(f"     {key}: ML модель (можно использовать для прогноза)")
                    elif isinstance(value, (list, tuple)):
                        print(f"     {key}: список/кортеж длиной {len(value)}")
                    elif isinstance(value, np.ndarray):
                        print(f"     {key}: numpy массив формы {value.shape}")
                    else:
                        print(f"     {key}: {type(value).__name__}")
                
                models_info.append({
                    'file': model_file,
                    'type': 'dict',
                    'keys': list(model_data.keys()),
                    'has_ml_models': any(hasattr(v, 'predict') for v in model_data.values() if hasattr(v, '__iter__'))
                })
                
            elif hasattr(model_data, 'predict'):
                print(f"   ✅ ML модель готова к использованию")
                print(f"   Методы: {[method for method in dir(model_data) if not method.startswith('_')]}")
                
                models_info.append({
                    'file': model_file,
                    'type': 'ml_model',
                    'ready': True
                })
                
            else:
                print(f"   ⚠️ Неизвестный тип данных")
                models_info.append({
                    'file': model_file,
                    'type': 'unknown',
                    'ready': False
                })
                
        except Exception as e:
            print(f"   ❌ Ошибка загрузки: {e}")
            models_info.append({
                'file': model_file,
                'error': str(e)
            })
    
    return models_info

def check_performance_data(csv_files):
    """Проверка данных о производительности моделей"""
    print(f"\n📊 ПРОВЕРКА ДАННЫХ О ПРОИЗВОДИТЕЛЬНОСТИ")
    print("=" * 50)
    
    performance_data = {}
    
    for csv_file in csv_files:
        if 'performance' in csv_file.lower() or 'accuracy' in csv_file.lower():
            try:
                print(f"\n📈 Файл производительности: {os.path.basename(csv_file)}")
                
                df = pd.read_csv(csv_file)
                print(f"   Размер: {df.shape}")
                print(f"   Колонки: {list(df.columns)}")
                
                if not df.empty:
                    print(f"   Первые строки:")
                    print(df.head().to_string())
                    
                    # Анализируем метрики
                    if 'accuracy' in df.columns or 'r2' in df.columns:
                        accuracy_col = 'accuracy' if 'accuracy' in df.columns else 'r2'
                        if accuracy_col in df.columns:
                            avg_accuracy = df[accuracy_col].mean()
                            print(f"   Средняя точность ({accuracy_col}): {avg_accuracy:.4f}")
                    
                    if 'mae' in df.columns:
                        avg_mae = df['mae'].mean()
                        print(f"   Средняя MAE: {avg_mae:.4f}")
                
                performance_data[os.path.basename(csv_file)] = {
                    'shape': df.shape,
                    'columns': list(df.columns),
                    'data': df.to_dict('records') if not df.empty else []
                }
                
            except Exception as e:
                print(f"   ❌ Ошибка чтения: {e}")
    
    return performance_data

def check_stock_data(csv_files):
    """Проверка данных о запасах"""
    print(f"\n📦 ПРОВЕРКА ДАННЫХ О ЗАПАСАХ")
    print("=" * 50)
    
    stock_data = {}
    
    for csv_file in csv_files:
        if 'stock' in csv_file.lower():
            try:
                print(f"\n🏭 Файл запасов: {os.path.basename(csv_file)}")
                
                df = pd.read_csv(csv_file)
                print(f"   Размер: {df.shape}")
                print(f"   Колонки: {list(df.columns)}")
                
                if not df.empty:
                    print(f"   Первые строки:")
                    print(df.head().to_string())
                    
                    # Анализируем данные
                    if 'product_code' in df.columns:
                        unique_products = df['product_code'].nunique()
                        print(f"   Уникальных продуктов: {unique_products}")
                    
                    if 'stock' in df.columns:
                        total_stock = df['stock'].sum()
                        avg_stock = df['stock'].mean()
                        print(f"   Общий запас: {total_stock:.2f}")
                        print(f"   Средний запас: {avg_stock:.2f}")
                
                stock_data[os.path.basename(csv_file)] = {
                    'shape': df.shape,
                    'columns': list(df.columns),
                    'data': df.to_dict('records') if not df.empty else []
                }
                
            except Exception as e:
                print(f"   ❌ Ошибка чтения: {e}")
    
    return stock_data

def generate_summary_report(models_info, performance_data, stock_data):
    """Генерация итогового отчета"""
    print(f"\n📋 ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 50)
    
    # Подсчитываем статистику
    total_models = len([m for m in models_info if m.get('ready', False)])
    total_files = len(models_info)
    ready_models = len([m for m in models_info if m.get('ready', False)])
    
    print(f"📊 СТАТИСТИКА:")
    print(f"   Всего файлов моделей: {total_files}")
    print(f"   Готовых ML моделей: {ready_models}")
    print(f"   Файлов производительности: {len(performance_data)}")
    print(f"   Файлов запасов: {len(stock_data)}")
    
    # Оценка готовности
    if ready_models > 0:
        print(f"\n✅ ML МОДЕЛИ ГОТОВЫ К ИСПОЛЬЗОВАНИЮ")
        print(f"   • Найдено {ready_models} готовых моделей")
        print(f"   • Модели можно использовать для прогнозирования")
        
        if performance_data:
            print(f"   • Есть данные о производительности моделей")
        
        if stock_data:
            print(f"   • Есть данные о запасах для прогнозирования")
            
    elif total_files > 0:
        print(f"\n⚠️ МОДЕЛИ НАЙДЕНЫ, НО ТРЕБУЮТ ПРОВЕРКИ")
        print(f"   • Найдено {total_files} файлов моделей")
        print(f"   • Необходимо проверить структуру данных")
        
    else:
        print(f"\n❌ ML МОДЕЛИ НЕ НАЙДЕНЫ")
        print(f"   • Проверьте директории: data/, services/moysklad-service/data/")
        print(f"   • Убедитесь, что модели были обучены")
    
    # Сохраняем отчет
    report = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_model_files': total_files,
            'ready_models': ready_models,
            'performance_files': len(performance_data),
            'stock_files': len(stock_data)
        },
        'models_info': models_info,
        'performance_data': performance_data,
        'stock_data': stock_data
    }
    
    with open('ml_models_local_check.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n💾 Отчет сохранен в файл: ml_models_local_check.json")

def main():
    """Основная функция"""
    print("🔍 ПРОВЕРКА ML-МОДЕЛЕЙ В ЛОКАЛЬНОЙ СРЕДЕ")
    print("=" * 60)
    print(f"📅 Время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Проверяем файлы моделей
    model_files, csv_files = check_model_files()
    
    if not model_files:
        print("\n❌ Файлы моделей не найдены!")
        print("   Проверьте директории:")
        print("   - data/")
        print("   - services/moysklad-service/data/")
        return
    
    # 2. Тестируем модели
    models_info = load_and_test_models(model_files)
    
    # 3. Проверяем данные о производительности
    performance_data = check_performance_data(csv_files)
    
    # 4. Проверяем данные о запасах
    stock_data = check_stock_data(csv_files)
    
    # 5. Генерируем отчет
    generate_summary_report(models_info, performance_data, stock_data)

if __name__ == "__main__":
    main()
