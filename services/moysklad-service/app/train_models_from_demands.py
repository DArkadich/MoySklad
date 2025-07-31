import os
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

class DemandsBasedTrainer:
    def __init__(self):
        self.data_path = "/app/data"
        self.models_path = "/app/ml-models"
        os.makedirs(self.models_path, exist_ok=True)
        
    def load_data(self):
        """Загружает данные из demands.csv"""
        demands_file = os.path.join(self.data_path, "demands.csv")
        if not os.path.exists(demands_file):
            logger.error(f"Файл {demands_file} не найден")
            return None
            
        logger.info(f"Загружаем данные из {demands_file}")
        df = pd.read_csv(demands_file)
        logger.info(f"Загружено {len(df)} записей")
        
        # Показываем структуру данных
        logger.info(f"Колонки: {df.columns.tolist()}")
        logger.info(f"Первые записи:\n{df.head()}")
        
        return df
    
    def extract_sales_by_product(self, df):
        """Извлекает продажи по товарам из документов продаж"""
        logger.info("Извлекаем продажи по товарам...")
        
        # Проверяем наличие необходимых колонок
        required_columns = ['product_code', 'product_name', 'quantity', 'date']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Отсутствуют колонки: {missing_columns}")
            return {}
        
        # Группируем по коду товара
        sales_by_product = {}
        
        for _, row in df.iterrows():
            product_code = row.get('product_code')
            product_name = row.get('product_name', 'Unknown')
            quantity = row.get('quantity', 0)
            date_str = row.get('date', '')
            
            if pd.isna(product_code) or pd.isna(quantity) or pd.isna(date_str):
                continue
                
            try:
                # Парсим дату
                date = pd.to_datetime(date_str).date()
                quantity = float(quantity)
                
                if product_code not in sales_by_product:
                    sales_by_product[product_code] = {
                        'name': product_name,
                        'sales': []
                    }
                
                sales_by_product[product_code]['sales'].append({
                    'date': date,
                    'quantity': quantity
                })
                
            except (ValueError, TypeError) as e:
                logger.debug(f"Ошибка парсинга строки: {e}")
                continue
        
        logger.info(f"Извлечено продаж для {len(sales_by_product)} товаров")
        
        # Показываем примеры
        for i, (code, data) in enumerate(sales_by_product.items()):
            if i < 3:  # Показываем первые 3 товара
                logger.info(f"Товар {code} ({data['name']}): {len(data['sales'])} продаж")
                if data['sales']:
                    logger.info(f"  Примеры: {data['sales'][:3]}")
        
        return sales_by_product
    
    def train_simple_models(self, sales_by_product):
        """Обучает простые модели на основе продаж"""
        logger.info("Обучаем модели...")
        
        trained_models = 0
        errors = 0
        
        for product_code, data in sales_by_product.items():
            try:
                if len(data['sales']) < 5:  # Минимум 5 продаж для обучения
                    logger.debug(f"Товар {product_code}: недостаточно данных ({len(data['sales'])} продаж)")
                    continue
                
                # Сортируем продажи по дате
                sales = sorted(data['sales'], key=lambda x: x['date'])
                
                # Вычисляем среднее потребление
                total_quantity = sum(sale['quantity'] for sale in sales)
                days_span = (sales[-1]['date'] - sales[0]['date']).days + 1
                
                if days_span == 0:
                    continue
                
                # Считаем количество дней с продажами (не 0)
                days_with_sales = len([sale for sale in sales if sale['quantity'] > 0])
                oos_days = len([sale for sale in sales if sale['quantity'] == 0])
                
                # Среднее потребление за день с продажами
                if days_with_sales > 0:
                    avg_consumption_per_sale_day = total_quantity / days_with_sales
                else:
                    avg_consumption_per_sale_day = 0
                
                # Среднее потребление за весь период (включая дни без продаж)
                avg_consumption_per_total_day = total_quantity / days_span
                
                # Используем среднее потребление за день с продажами для планирования
                avg_consumption = avg_consumption_per_sale_day
                
                # Определяем критический остаток (50% от среднего потребления, минимум 3)
                critical_stock = max(3, avg_consumption * 0.5)
                
                # Сохраняем модель
                model_data = {
                    'product_code': product_code,
                    'product_name': data['name'],
                    'avg_consumption': avg_consumption,
                    'avg_consumption_per_total_day': avg_consumption_per_total_day,
                    'critical_stock': critical_stock,
                    'total_sales': total_quantity,
                    'sales_count': len(sales),
                    'days_with_sales': days_with_sales,
                    'days_span': days_span,
                    'oos_days': oos_days,
                    'last_sale_date': sales[-1]['date'].isoformat(),
                    'first_sale_date': sales[0]['date'].isoformat()
                }
                
                # Сохраняем в CSV
                model_file = os.path.join(self.models_path, f"model_{product_code}.csv")
                pd.DataFrame([model_data]).to_csv(model_file, index=False)
                
                trained_models += 1
                logger.info(f"Обучена модель для {product_code} ({data['name']}): "
                          f"среднее потребление {avg_consumption:.2f} (за день с продажами), "
                          f"критический остаток {critical_stock:.1f}")
                
            except Exception as e:
                errors += 1
                logger.error(f"Ошибка обучения модели для {product_code}: {e}")
        
        logger.info(f"Обучение завершено. Успешно: {trained_models}, Ошибок: {errors}")
        return trained_models, errors

async def main():
    trainer = DemandsBasedTrainer()
    
    # Загружаем данные
    df = trainer.load_data()
    if df is None:
        return
    
    # Извлекаем продажи по товарам
    sales_by_product = trainer.extract_sales_by_product(df)
    
    if not sales_by_product:
        logger.error("Не удалось извлечь продажи по товарам")
        return
    
    # Обучаем модели
    trainer.train_simple_models(sales_by_product)

if __name__ == "__main__":
    asyncio.run(main()) 