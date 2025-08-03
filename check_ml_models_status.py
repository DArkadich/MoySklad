#!/usr/bin/env python3
"""
Проверка статуса ML-моделей
"""

import os
import pickle
import pandas as pd
from datetime import datetime
import json

def check_models_status():
    """Проверка статуса ML-моделей"""
    
    print("🔍 ПРОВЕРКА СТАТУСА ML-МОДЕЛЕЙ")
    print("=" * 50)
    
    # Проверка наличия файлов моделей
    print("\n1️⃣ Проверка файлов моделей...")
    
    model_files = {
        "universal_forecast_models.pkl": "data/universal_forecast_models.pkl",
        "universal_model_performance.csv": "data/universal_model_performance.csv",
        "accurate_consumption_results.csv": "data/accurate_consumption_results.csv",
        "production_stock_data.csv": "data/production_stock_data.csv"
    }
    
    models_found = 0
    for name, path in model_files.items():
        if os.path.exists(path):
            size = os.path.getsize(path)
            size_mb = size / (1024 * 1024)
            print(f"✅ {name}: {size_mb:.2f} MB")
            models_found += 1
        else:
            print(f"❌ {name}: не найден")
    
    print(f"\n📊 Найдено файлов моделей: {models_found}/{len(model_files)}")
    
    # Проверка производительности моделей
    print("\n2️⃣ Проверка производительности моделей...")
    
    if os.path.exists("data/universal_model_performance.csv"):
        try:
            performance_df = pd.read_csv("data/universal_model_performance.csv")
            print("📈 Метрики производительности:")
            for _, row in performance_df.iterrows():
                model = row['model']
                mae = row['mae']
                r2 = row['r2']
                print(f"   • {model}: MAE={mae:.4f}, R²={r2:.4f}")
        except Exception as e:
            print(f"❌ Ошибка чтения метрик: {e}")
    
    # Проверка данных для обучения
    print("\n3️⃣ Проверка данных для обучения...")
    
    if os.path.exists("data/accurate_consumption_results.csv"):
        try:
            consumption_df = pd.read_csv("data/accurate_consumption_results.csv")
            print(f"📊 Данные потребления: {len(consumption_df)} записей")
            print(f"   • Продукты: {consumption_df['product_code'].nunique()}")
            print(f"   • Период: {consumption_df['start_date'].min()} - {consumption_df['start_date'].max()}")
        except Exception as e:
            print(f"❌ Ошибка чтения данных потребления: {e}")
    
    # Проверка данных о запасах
    if os.path.exists("data/production_stock_data.csv"):
        try:
            stock_df = pd.read_csv("data/production_stock_data.csv")
            print(f"📦 Данные о запасах: {len(stock_df)} записей")
            if 'product_code' in stock_df.columns:
                print(f"   • Продукты: {stock_df['product_code'].nunique()}")
        except Exception as e:
            print(f"❌ Ошибка чтения данных о запасах: {e}")
    
    # Проверка загруженных моделей
    print("\n4️⃣ Проверка загруженных моделей...")
    
    if os.path.exists("data/universal_forecast_models.pkl"):
        try:
            with open("data/universal_forecast_models.pkl", "rb") as f:
                models = pickle.load(f)
            
            if isinstance(models, dict):
                print(f"✅ Загружено моделей: {len(models)}")
                for model_name, model_info in models.items():
                    if isinstance(model_info, dict):
                        print(f"   • {model_name}: {type(model_info.get('model', 'Unknown')).__name__}")
                    else:
                        print(f"   • {model_name}: {type(model_info).__name__}")
            else:
                print(f"✅ Загружена модель: {type(models).__name__}")
                
        except Exception as e:
            print(f"❌ Ошибка загрузки моделей: {e}")
    
    # Общая оценка
    print("\n5️⃣ ОБЩАЯ ОЦЕНКА:")
    
    if models_found >= 3:
        print("✅ ML-модели обучены и готовы к использованию")
        print("   • Файлы моделей присутствуют")
        print("   • Данные для обучения доступны")
        print("   • Метрики производительности загружены")
    elif models_found >= 2:
        print("⚠️  ML-модели частично готовы")
        print("   • Некоторые файлы отсутствуют")
        print("   • Рекомендуется переобучение")
    else:
        print("❌ ML-модели не обучены")
        print("   • Необходимо обучить модели")
        print("   • Запустите: python3 train_initial_models.py")
    
    print(f"\n📅 Проверка выполнена: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    check_models_status() 