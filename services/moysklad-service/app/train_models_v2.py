#!/usr/bin/env python3
"""
Новая версия обучения ML-моделей с использованием данных остатков
"""

import pandas as pd
import numpy as np
import json
import logging
import os
from datetime import datetime
from pathlib import Path

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockBasedTrainer:
    """Тренер моделей на основе данных остатков"""
    
    def __init__(self):
        self.models_dir = "/app/models"
        os.makedirs(self.models_dir, exist_ok=True)
        
    def load_data(self):
        """Загрузка данных из CSV файлов"""
        logger.info("Загрузка данных из CSV файлов...")
        
        # Поиск файлов
        possible_sales_paths = [
            "/app/data/sales_history.csv",
            "sales_history.csv",
            "/app/sales_history.csv",
            "/app/app/sales_history.csv",
            "../sales_history.csv",
            "app/sales_history.csv"
        ]
        
        possible_stock_paths = [
            "/app/data/stock_history.csv",
            "stock_history.csv",
            "/app/stock_history.csv",
            "/app/app/stock_history.csv",
            "../stock_history.csv",
            "app/stock_history.csv"
        ]
        
        # Поиск файла продаж
        sales_file = None
        for path in possible_sales_paths:
            if Path(path).exists():
                sales_file = path
                logger.info(f"Найден файл продаж: {sales_file}")
                break
        
        if not sales_file:
            logger.error("Файл продаж не найден!")
            return None, None
        
        # Поиск файла остатков
        stock_file = None
        for path in possible_stock_paths:
            if Path(path).exists():
                stock_file = path
                logger.info(f"Найден файл остатков: {stock_file}")
                break
        
        if not stock_file:
            logger.error("Файл остатков не найден!")
            return None, None
        
        # Загрузка данных
        try:
            sales_df = pd.read_csv(sales_file)
            stock_df = pd.read_csv(stock_file)
            
            logger.info(f"Загружено {len(sales_df)} записей продаж")
            logger.info(f"Загружено {len(stock_df)} записей остатков")
            
            return sales_df, stock_df
            
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")
            return None, None
    
    def extract_product_info_from_stock(self, stock_df):
        """Извлечение информации о товарах из данных остатков"""
        logger.info("Извлечение информации о товарах из остатков...")
        
        if 'code' not in stock_df.columns:
            logger.error("Поле 'code' не найдено в данных остатков")
            return {}
        
        # Создаем словарь товаров по коду
        products = {}
        
        for _, row in stock_df.iterrows():
            code = row.get('code')
            name = row.get('name', '')
            meta = row.get('meta', '')
            
            if pd.notna(code) and code:
                # Извлекаем ID товара из meta
                product_id = None
                if pd.notna(meta) and meta:
                    try:
                        meta_data = json.loads(meta.replace("'", '"'))
                        if 'href' in meta_data:
                            href = meta_data['href']
                            if '/entity/product/' in href:
                                product_id = href.split('/entity/product/')[1].split('/')[0]
                            elif '/entity/service/' in href:
                                product_id = f"service_{href.split('/entity/service/')[1].split('/')[0]}"
                    except:
                        pass
                
                # Используем код как ключ
                products[code] = {
                    'name': name,
                    'product_id': product_id,
                    'code': code
                }
        
        logger.info(f"Извлечено {len(products)} уникальных товаров из остатков")
        return products
    
    def extract_sales_by_product(self, sales_df, products):
        """Извлечение продаж по товарам"""
        logger.info("Извлечение продаж по товарам...")
        
        if 'positions' not in sales_df.columns:
            logger.error("Поле 'positions' не найдено в данных продаж")
            return {}
        
        sales_by_product = {}
        
        for _, row in sales_df.iterrows():
            positions_str = row.get('positions', '')
            moment = row.get('moment', '')
            
            if pd.notna(positions_str) and positions_str:
                # Извлекаем ID товара из positions
                product_id = self._extract_product_id_from_positions(positions_str)
                
                if product_id and product_id != "unknown":
                    # Ищем товар по ID в словаре продуктов
                    product_code = None
                    for code, product_info in products.items():
                        if product_info.get('product_id') == product_id:
                            product_code = code
                            break
                    
                    if product_code:
                        if product_code not in sales_by_product:
                            sales_by_product[product_code] = []
                        
                        # Парсим дату
                        try:
                            if pd.notna(moment):
                                date = pd.to_datetime(moment).date()
                                # Извлекаем количество из positions
                                quantity = self._extract_quantity_from_positions(positions_str)
                                sales_by_product[product_code].append({
                                    'date': date,
                                    'quantity': quantity
                                })
                        except Exception as e:
                            logger.debug(f"Ошибка обработки записи: {e}")
                else:
                    # Отладочная информация для первых записей
                    if len(sales_by_product) == 0:
                        logger.info(f"DEBUG: Не удалось извлечь product_id из positions: {positions_str[:200]}...")
                        logger.info(f"DEBUG: Извлеченный product_id: {product_id}")
                        logger.info(f"DEBUG: Доступные product_ids в остатках: {list(products.keys())[:5]}")
                        logger.info(f"DEBUG: Примеры product_info: {list(products.values())[:2]}")
        
        logger.info(f"Извлечено продаж для {len(sales_by_product)} товаров")
        return sales_by_product
    
    def _extract_quantity_from_positions(self, positions_str):
        """Извлечение количества из строки positions"""
        try:
            positions_str_fixed = positions_str.replace("'", '"')
            positions_data = json.loads(positions_str_fixed)
            
            # Проверяем, является ли это мета-информацией о позициях
            if 'meta' in positions_data and 'href' in positions_data['meta']:
                # Это мета-информация, пока используем 1 как значение по умолчанию
                return 1.0
            
            # Если это массив позиций
            if isinstance(positions_data, list) and len(positions_data) > 0:
                total_quantity = 0
                for position in positions_data:
                    quantity = position.get('quantity', 0)
                    total_quantity += float(quantity)
                return total_quantity
        except:
            pass
        return 1.0  # Значение по умолчанию
    
    def _extract_product_id_from_positions(self, positions_str):
        """Извлечение ID товара из строки positions"""
        try:
            # Пробуем заменить одинарные кавычки на двойные
            positions_str_fixed = positions_str.replace("'", '"')
            positions_data = json.loads(positions_str_fixed)
            
            # Проверяем, является ли это мета-информацией
            if 'meta' in positions_data and 'href' in positions_data['meta']:
                href = positions_data['meta']['href']
                logger.debug(f"DEBUG: Обрабатываем href: {href}")
                if '/entity/product/' in href:
                    product_id = href.split('/entity/product/')[1].split('/')[0]
                    logger.debug(f"DEBUG: Извлечен product_id: {product_id}")
                    return product_id
                elif '/entity/service/' in href:
                    service_id = href.split('/entity/service/')[1].split('/')[0]
                    logger.debug(f"DEBUG: Извлечен service_id: {service_id}")
                    return f"service_{service_id}"
            
            # Если это массив позиций
            if isinstance(positions_data, list) and len(positions_data) > 0:
                for position in positions_data:
                    assortment = position.get('assortment', {})
                    meta = assortment.get('meta', {})
                    href = meta.get('href', '')
                    
                    if href and '/entity/product/' in href:
                        product_id = href.split('/entity/product/')[1].split('/')[0]
                        logger.debug(f"DEBUG: Извлечен product_id из позиции: {product_id}")
                        return product_id
                    elif href and '/entity/service/' in href:
                        service_id = href.split('/entity/service/')[1].split('/')[0]
                        logger.debug(f"DEBUG: Извлечен service_id из позиции: {service_id}")
                        return f"service_{service_id}"
            
        except Exception as e:
            logger.debug(f"Ошибка извлечения ID товара: {e}")
        
        return "unknown"
    
    def train_simple_models(self, sales_by_product, stock_df):
        """Обучение простых моделей с учетом OoS дней"""
        logger.info("Начинаем обучение простых моделей с учетом OoS дней...")
        
        successful_models = 0
        failed_models = 0
        
        for product_code, sales_data in sales_by_product.items():
            if len(sales_data) < 3:  # Минимум 3 записи
                logger.warning(f"Недостаточно данных для товара {product_code}: {len(sales_data)} записей")
                failed_models += 1
                continue
            
            try:
                # Создаем DataFrame из продаж
                df = pd.DataFrame(sales_data)
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')
                
                # Получаем данные остатков для этого товара
                product_stock = stock_df[stock_df['code'] == product_code].copy()
                if len(product_stock) > 0:
                    product_stock['date'] = pd.to_datetime(product_stock['date'])
                    
                    # Определяем критический остаток (когда товар "фактически" закончился)
                    # Анализируем историю продаж для определения среднего потребления
                    if len(df) >= 5:  # Нужно минимум 5 записей для анализа
                        recent_sales = df.tail(10)  # Последние 10 продаж
                        avg_recent_consumption = recent_sales['quantity'].mean()
                        critical_stock = max(avg_recent_consumption * 0.5, 3)  # 50% от среднего или минимум 3 шт.
                    else:
                        critical_stock = 3  # По умолчанию критический остаток = 3 шт.
                    
                    # Фильтруем продажи, исключая дни с критическим остатком (OoS)
                    valid_sales = []
                    for _, sale in df.iterrows():
                        sale_date = sale['date']
                        # Проверяем остаток на эту дату или ближайшую предыдущую
                        stock_on_date = product_stock[product_stock['date'] <= sale_date]
                        if len(stock_on_date) > 0:
                            # Берем остаток на ближайшую дату
                            latest_stock = stock_on_date.iloc[-1]
                            if latest_stock['quantity'] > critical_stock:  # Товар был в достаточном количестве
                                valid_sales.append(sale)
                    
                    if len(valid_sales) >= 3:  # Минимум 3 валидные записи
                        valid_df = pd.DataFrame(valid_sales)
                        avg_consumption = valid_df['quantity'].mean()
                        total_sales = len(valid_df)
                        oos_filtered = len(df) - len(valid_df)
                        
                        logger.info(f"Товар {product_code}: {len(valid_df)} валидных продаж из {len(df)} (исключено {oos_filtered} OoS дней, критический остаток = {critical_stock:.1f})")
                    else:
                        # Если мало валидных продаж, используем все данные
                        avg_consumption = df['quantity'].mean()
                        total_sales = len(df)
                        logger.warning(f"Товар {product_code}: мало валидных продаж, используем все данные")
                else:
                    # Если нет данных об остатках, используем все продажи
                    avg_consumption = df['quantity'].mean()
                    total_sales = len(df)
                    logger.warning(f"Товар {product_code}: нет данных об остатках")
                
                # Сохраняем модель
                model_data = {
                    'product_code': product_code,
                    'avg_consumption': float(avg_consumption),
                    'total_sales': total_sales,
                    'date_range': {
                        'start': df['date'].min().strftime('%Y-%m-%d'),
                        'end': df['date'].max().strftime('%Y-%m-%d')
                    },
                    'last_updated': datetime.now().isoformat()
                }
                
                model_file = os.path.join(self.models_dir, f"{product_code}_model.json")
                with open(model_file, 'w', encoding='utf-8') as f:
                    json.dump(model_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"Модель для товара {product_code}: среднее потребление = {avg_consumption:.2f}")
                successful_models += 1
                
            except Exception as e:
                logger.error(f"Ошибка обучения модели для товара {product_code}: {e}")
                failed_models += 1
        
        logger.info(f"Обучение завершено. Успешно: {successful_models}, Ошибок: {failed_models}")
        return successful_models, failed_models
    
    def run(self):
        """Запуск процесса обучения"""
        logger.info("Запуск обучения ML-моделей на основе данных остатков...")
        
        # Загрузка данных
        sales_df, stock_df = self.load_data()
        if sales_df is None or stock_df is None:
            return
        
        # Извлечение информации о товарах из остатков
        products = self.extract_product_info_from_stock(stock_df)
        
        # Извлечение продаж по товарам
        sales_by_product = self.extract_sales_by_product(sales_df, products)
        
        # Обучение моделей
        successful, failed = self.train_simple_models(sales_by_product, stock_df)
        
        logger.info(f"Обучение завершено! Успешно обучено моделей: {successful}, Ошибок: {failed}")

def main():
    """Основная функция"""
    trainer = StockBasedTrainer()
    trainer.run()

if __name__ == "__main__":
    main() 