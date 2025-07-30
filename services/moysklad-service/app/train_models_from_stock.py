#!/usr/bin/env python3
"""
Тренер ML-моделей на основе анализа изменений остатков
Определяем продажи через изменения остатков товаров
"""

import pandas as pd
import numpy as np
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockBasedTrainer:
    """Тренер моделей на основе анализа изменений остатков"""
    
    def __init__(self):
        self.models_dir = "/app/models"
        os.makedirs(self.models_dir, exist_ok=True)
        
    def load_data(self):
        """Загрузка данных изменений остатков"""
        logger.info("Загрузка данных изменений остатков...")
        
        # Поиск файлов
        possible_paths = [
            "/app/data/stock_changes.csv",
            "stock_changes.csv",
            "/app/stock_changes.csv"
        ]
        
        # Поиск файла
        stock_file = None
        for path in possible_paths:
            if Path(path).exists():
                stock_file = path
                logger.info(f"Найден файл изменений остатков: {stock_file}")
                break
        
        if not stock_file:
            logger.error("Файл изменений остатков не найден!")
            return None
        
        # Загрузка данных
        try:
            df = pd.read_csv(stock_file)
            logger.info(f"Загружено {len(df)} записей изменений остатков")
            
            # Отладочная информация о структуре данных
            if len(df) > 0:
                logger.info(f"Колонки данных: {list(df.columns)}")
                logger.info(f"Первые 3 записи:")
                for i in range(min(3, len(df))):
                    logger.info(f"  Запись {i+1}: {dict(df.iloc[i])}")
            
            return df
            
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")
            return None
    
    def analyze_stock_changes(self, df):
        """Анализ изменений остатков для определения продаж"""
        logger.info("Анализ изменений остатков для определения продаж...")
        
        # Группируем по товарам
        products = df.groupby('product_code')
        logger.info(f"Найдено {len(products)} уникальных товаров")
        
        sales_by_product = {}
        
        for product_code, group in products:
            if pd.isna(product_code) or product_code == '':
                continue
                
            # Сортируем по дате
            group = group.sort_values('date')
            
            # Анализируем изменения остатков
            sales_data = self._calculate_sales_from_stock_changes(group)
            
            if sales_data:
                sales_by_product[product_code] = {
                    'sales': sales_data,
                    'product_name': group['product_name'].iloc[0] if len(group) > 0 else '',
                    'total_records': len(group)
                }
        
        logger.info(f"Извлечено данных о продажах для {len(sales_by_product)} товаров")
        return sales_by_product
    
    def _calculate_sales_from_stock_changes(self, group):
        """Вычисление продаж на основе изменений остатков"""
        sales = []
        
        # Сортируем по дате
        group = group.sort_values('date')
        
        # Анализируем изменения между записями
        for i in range(1, len(group)):
            prev_record = group.iloc[i-1]
            curr_record = group.iloc[i]
            
            prev_date = pd.to_datetime(prev_record['date'])
            curr_date = pd.to_datetime(curr_record['date'])
            
            # Вычисляем изменение остатков
            prev_available = prev_record['available']
            curr_available = curr_record['available']
            
            # Если остаток уменьшился, это может быть продажа
            if curr_available < prev_available:
                # Вычисляем количество проданного товара
                sold_quantity = prev_available - curr_available
                
                # Проверяем, что это разумное количество (не слишком большое)
                if 0 < sold_quantity <= 100:  # Максимум 100 единиц за раз
                    sales.append({
                        'date': curr_date.date(),
                        'quantity': sold_quantity,
                        'prev_stock': prev_available,
                        'curr_stock': curr_available,
                        'change': sold_quantity
                    })
        
        return sales
    
    def train_models(self, sales_by_product):
        """Обучение моделей на основе данных о продажах"""
        logger.info("Начинаем обучение моделей на основе изменений остатков...")
        
        successful_models = 0
        failed_models = 0
        
        for product_code, data in sales_by_product.items():
            sales = data['sales']
            product_name = data['product_name']
            
            if len(sales) < 3:  # Минимум 3 продажи
                logger.warning(f"Недостаточно данных для товара {product_code} ({product_name}): {len(sales)} продаж")
                failed_models += 1
                continue
            
            try:
                # Создаем DataFrame из продаж
                df = pd.DataFrame(sales)
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')
                
                # Вычисляем среднее потребление
                avg_consumption = df['quantity'].mean()
                total_sales = len(df)
                
                # Определяем критический остаток (когда товар "фактически" закончился)
                if len(df) >= 5:
                    recent_sales = df.tail(10)  # Последние 10 продаж
                    avg_recent_consumption = recent_sales['quantity'].mean()
                    critical_stock = max(avg_recent_consumption * 0.5, 3)  # 50% от среднего или минимум 3 шт.
                else:
                    critical_stock = 3
                
                # Фильтруем продажи, исключая дни с критическим остатком (OoS)
                valid_sales = []
                for _, sale in df.iterrows():
                    if sale['prev_stock'] > critical_stock:  # Товар был в достаточном количестве
                        valid_sales.append(sale)
                
                if len(valid_sales) >= 3:
                    valid_df = pd.DataFrame(valid_sales)
                    avg_consumption = valid_df['quantity'].mean()
                    oos_filtered = len(df) - len(valid_df)
                    
                    logger.info(f"Товар {product_code} ({product_name}): {len(valid_df)} валидных продаж из {len(df)} (исключено {oos_filtered} OoS дней, критический остаток = {critical_stock:.1f})")
                else:
                    # Если мало валидных продаж, используем все данные
                    avg_consumption = df['quantity'].mean()
                    logger.warning(f"Товар {product_code} ({product_name}): мало валидных продаж, используем все данные")
                
                # Сохраняем модель
                model_data = {
                    'product_code': product_code,
                    'product_name': product_name,
                    'avg_consumption': float(avg_consumption),
                    'total_sales': total_sales,
                    'critical_stock': float(critical_stock),
                    'date_range': {
                        'start': df['date'].min().strftime('%Y-%m-%d'),
                        'end': df['date'].max().strftime('%Y-%m-%d')
                    },
                    'last_updated': datetime.now().isoformat()
                }
                
                model_file = os.path.join(self.models_dir, f"{product_code}_model.json")
                with open(model_file, 'w', encoding='utf-8') as f:
                    json.dump(model_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"Модель для товара {product_code} ({product_name}): среднее потребление = {avg_consumption:.2f}")
                successful_models += 1
                
            except Exception as e:
                logger.error(f"Ошибка обучения модели для товара {product_code}: {e}")
                failed_models += 1
        
        logger.info(f"Обучение завершено. Успешно: {successful_models}, Ошибок: {failed_models}")
        return successful_models, failed_models
    
    def run(self):
        """Запуск процесса обучения"""
        logger.info("Запуск обучения ML-моделей на основе изменений остатков...")
        
        # Загрузка данных
        df = self.load_data()
        if df is None:
            return
        
        # Анализ изменений остатков
        sales_by_product = self.analyze_stock_changes(df)
        
        # Обучение моделей
        successful, failed = self.train_models(sales_by_product)
        
        logger.info(f"Обучение завершено! Успешно обучено моделей: {successful}, Ошибок: {failed}")

def main():
    """Основная функция"""
    trainer = StockBasedTrainer()
    trainer.run()

if __name__ == "__main__":
    main() 