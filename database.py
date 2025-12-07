# database.py - работа с базой данных через SQLAlchemy
import os
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
import sqlite3

class Database:
    def __init__(self):
        self.db_path = "restaurant.db"
        self.engine = None
        self.Session = None
        self._init_database()

    def _init_database(self):
        """Инициализация базы данных"""
        # Подключаемся к БД
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        self.Session = sessionmaker(bind=self.engine)

        # Если файл БД не существует, создаем из SQL файла
        if not os.path.exists(self.db_path):
            print(f"🔄 Создаем БД из SQL файла...")
            self._create_database_from_sql()
        else:
            print(f"✅ БД уже существует, подключаемся...")

    def _create_database_from_sql(self):
        """Создать БД из SQL файла"""
        sql_file = "database_schema.sql"
        if not os.path.exists(sql_file):
            raise FileNotFoundError(f"❌ SQL файл {sql_file} не найден")

        try:
            # Читаем SQL файл
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            print(f"📖 Читаем SQL файл: {sql_file}")

            # Создаем подключение к SQLite
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Включаем поддержку внешних ключей
            cursor.execute("PRAGMA foreign_keys = ON;")

            # Выполняем весь SQL скрипт
            cursor.executescript(sql_content)
            conn.commit()
            conn.close()

            print("✅ БД создана из SQL файла")

        except Exception as e:
            print(f"❌ Ошибка при создании БД из SQL: {e}")
            raise

    # ========== ПОЛЬЗОВАТЕЛИ ==========
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Получить всех пользователей"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, login, birth_date, diet_type, meal_style 
                    FROM users 
                    ORDER BY id
                """))
                return [dict(row._mapping) for row in result]
        except Exception as e:
            print(f"❌ Ошибка при получении пользователей: {e}")
            return []

    def delete_user(self, user_id: int) -> bool:
        """Удалить пользователя"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("DELETE FROM users WHERE id = :id"),
                    {"id": user_id}
                )
                conn.commit()
                return result.rowcount > 0
        except Exception as e:
            print(f"❌ Ошибка при удалении пользователя: {e}")
            return False

    # ========== БЛЮДА (DISHES) ==========
    def get_all_dishes(self, category_id: Optional[int] = None, available_only: bool = False) -> List[Dict[str, Any]]:
        """Получить все блюда"""
        try:
            with self.engine.connect() as conn:
                query = "SELECT * FROM dishes WHERE 1=1"
                params = {}

                if category_id:
                    query += " AND category_id = :category_id"
                    params["category_id"] = category_id

                if available_only:
                    query += " AND is_available = 1"

                query += " ORDER BY name"

                result = conn.execute(text(query), params)
                dishes = []

                for row in result:
                    dish = dict(row._mapping)
                    # Конвертируем INTEGER в bool для SQLite
                    dish['is_available'] = bool(dish.get('is_available', 0))
                    dish['category_name'] = self._get_category_name(dish.get('category_id'))
                    dishes.append(dish)

                return dishes
        except Exception as e:
            print(f"❌ Ошибка при получении блюд: {e}")
            return []

    def _get_category_name(self, category_id: Optional[int]) -> Optional[str]:
        """Получить название категории по ID"""
        if not category_id:
            return None

        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT name FROM visit_categories WHERE id = :id"),
                    {"id": category_id}
                )
                row = result.fetchone()
                return row[0] if row else None
        except:
            return None

    def get_dish_by_id(self, dish_id: int) -> Optional[Dict[str, Any]]:
        """Получить блюдо по ID"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT * FROM dishes WHERE id = :id"),
                    {"id": dish_id}
                )
                row = result.fetchone()
                if row:
                    dish = dict(row._mapping)
                    dish['is_available'] = bool(dish.get('is_available', 0))
                    dish['category_name'] = self._get_category_name(dish.get('category_id'))
                    return dish
                return None
        except Exception as e:
            print(f"❌ Ошибка при получении блюда: {e}")
            return None

    def create_dish(self, dish_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создать новое блюдо"""
        try:
            with self.engine.connect() as conn:
                if 'is_available' in dish_data:
                    dish_data['is_available'] = 1 if dish_data['is_available'] else 0

                result = conn.execute(
                    text("""
                        INSERT INTO dishes (name, description, price, category_id, is_available)
                        VALUES (:name, :description, :price, :category_id, :is_available)
                    """),
                    dish_data
                )
                conn.commit()

                dish_id = result.lastrowid
                return self.get_dish_by_id(dish_id) or dish_data
        except Exception as e:
            print(f"❌ Ошибка при создании блюда: {e}")
            raise

    def update_dish(self, dish_id: int, dish_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обновить блюдо"""
        try:
            with self.engine.connect() as conn:
                if 'is_available' in dish_data:
                    dish_data['is_available'] = 1 if dish_data['is_available'] else 0

                set_parts = []
                params = {"id": dish_id}

                for key, value in dish_data.items():
                    if value is not None and key != 'id':
                        set_parts.append(f"{key} = :{key}")
                        params[key] = value

                if not set_parts:
                    return self.get_dish_by_id(dish_id)

                query = f"UPDATE dishes SET {', '.join(set_parts)} WHERE id = :id"
                result = conn.execute(text(query), params)
                conn.commit()

                if result.rowcount > 0:
                    return self.get_dish_by_id(dish_id)
                return None
        except Exception as e:
            print(f"❌ Ошибка при обновлении блюда: {e}")
            raise

    def delete_dish(self, dish_id: int) -> bool:
        """Удалить блюдо"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("DELETE FROM dishes WHERE id = :id"),
                    {"id": dish_id}
                )
                conn.commit()
                return result.rowcount > 0
        except Exception as e:
            print(f"❌ Ошибка при удалении блюда: {e}")
            return False

    # ========== КАТЕГОРИИ ==========
    def get_all_categories(self) -> List[Dict[str, Any]]:
        """Получить все категории"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT id, name, NULL as description FROM visit_categories ORDER BY name"))
                return [dict(row._mapping) for row in result]
        except Exception as e:
            print(f"❌ Ошибка при получении категорий: {e}")
            return []

    # ========== НАПИТКИ (BAR ITEMS) ==========
    def get_all_bar_items(self) -> List[Dict[str, Any]]:
        """Получить все напитки"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT * FROM bar_items ORDER BY name"))
                items = []
                for row in result:
                    item = dict(row._mapping)
                    # Конвертируем INTEGER в bool для SQLite
                    item['is_alcoholic'] = bool(item.get('is_alcoholic', 0))
                    item['is_available'] = bool(item.get('is_available', 0))
                    items.append(item)
                return items
        except Exception as e:
            print(f"❌ Ошибка при получении напитков: {e}")
            return []

    def get_bar_item_by_id(self, item_id: int) -> Optional[Dict[str, Any]]:
        """Получить напиток по ID"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT * FROM bar_items WHERE id = :id"),
                    {"id": item_id}
                )
                row = result.fetchone()
                if row:
                    item = dict(row._mapping)
                    item['is_alcoholic'] = bool(item.get('is_alcoholic', 0))
                    item['is_available'] = bool(item.get('is_available', 0))
                    return item
                return None
        except Exception as e:
            print(f"❌ Ошибка при получении напитка: {e}")
            return None

    def create_bar_item(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создать новый напиток"""
        try:
            with self.engine.connect() as conn:
                if 'is_available' in item_data:
                    item_data['is_available'] = 1 if item_data['is_available'] else 0
                if 'is_alcoholic' in item_data:
                    item_data['is_alcoholic'] = 1 if item_data['is_alcoholic'] else 0

                result = conn.execute(
                    text("""
                        INSERT INTO bar_items (name, description, price, is_alcoholic, strength, is_available)
                        VALUES (:name, :description, :price, :is_alcoholic, :strength, :is_available)
                    """),
                    item_data
                )
                conn.commit()

                item_id = result.lastrowid
                return self.get_bar_item_by_id(item_id) or item_data
        except Exception as e:
            print(f"❌ Ошибка при создании напитка: {e}")
            raise

    def update_bar_item(self, item_id: int, item_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обновить напиток"""
        try:
            with self.engine.connect() as conn:
                if 'is_available' in item_data:
                    item_data['is_available'] = 1 if item_data['is_available'] else 0
                if 'is_alcoholic' in item_data:
                    item_data['is_alcoholic'] = 1 if item_data['is_alcoholic'] else 0

                set_parts = []
                params = {"id": item_id}

                for key, value in item_data.items():
                    if value is not None and key != 'id':
                        set_parts.append(f"{key} = :{key}")
                        params[key] = value

                if not set_parts:
                    return self.get_bar_item_by_id(item_id)

                query = f"UPDATE bar_items SET {', '.join(set_parts)} WHERE id = :id"
                result = conn.execute(text(query), params)
                conn.commit()

                if result.rowcount > 0:
                    return self.get_bar_item_by_id(item_id)
                return None
        except Exception as e:
            print(f"❌ Ошибка при обновлении напитка: {e}")
            raise

    def delete_bar_item(self, item_id: int) -> bool:
        """Удалить напиток"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("DELETE FROM bar_items WHERE id = :id"),
                    {"id": item_id}
                )
                conn.commit()
                return result.rowcount > 0
        except Exception as e:
            print(f"❌ Ошибка при удалении напитка: {e}")
            return False

    # ========== ОБЩИЕ МЕТОДЫ ==========
    def get_all_tables(self) -> List[str]:
        """Получить список всех таблиц в БД"""
        try:
            inspector = inspect(self.engine)
            return inspector.get_table_names()
        except:
            return []

    def get_table_data(self, table_name: str) -> List[Dict[str, Any]]:
        """Получить все данные из таблицы (для отладки)"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT * FROM {table_name}"))
                return [dict(row._mapping) for row in result]
        except Exception as e:
            print(f"❌ Ошибка при получении данных из {table_name}: {e}")
            return []

    def get_users_count(self) -> int:
        """Получить количество пользователей"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM users"))
                return result.scalar() or 0
        except:
            return 0

    def get_dishes_count(self) -> int:
        """Получить количество блюд"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM dishes"))
                return result.scalar() or 0
        except:
            return 0

    def get_bar_items_count(self) -> int:
        """Получить количество напитков"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM bar_items"))
                return result.scalar() or 0
        except:
            return 0

    def get_all_ingredients(self) -> List[Dict[str, Any]]:
        """Получить все ингредиенты"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT * FROM ingredients ORDER BY name"))
                ingredients = []
                for row in result:
                    ingredient = dict(row._mapping)
                    # Конвертируем значения REAL в float
                    ingredient['current_stock'] = float(ingredient.get('current_stock', 0))
                    ingredient['min_stock_level'] = float(ingredient.get('min_stock_level', 0))
                    ingredients.append(ingredient)
                return ingredients
        except Exception as e:
            print(f"❌ Ошибка при получении ингредиентов: {e}")
            return []

    def create_ingredient(self, ingredient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создать новый ингредиент"""
        try:
            with self.engine.connect() as conn:
                # Преобразуем float в строки для SQLite
                for field in ['current_stock', 'min_stock_level']:
                    if field in ingredient_data:
                        ingredient_data[field] = float(ingredient_data[field])

                result = conn.execute(
                    text("""
                        INSERT INTO ingredients (name, unit, current_stock, min_stock_level)
                        VALUES (:name, :unit, :current_stock, :min_stock_level)
                    """),
                    ingredient_data
                )
                conn.commit()

                ingredient_id = result.lastrowid
                # Возвращаем созданный ингредиент
                with self.engine.connect() as conn2:
                    result2 = conn2.execute(
                        text("SELECT * FROM ingredients WHERE id = :id"),
                        {"id": ingredient_id}
                    )
                    row = result2.fetchone()
                    if row:
                        ingredient = dict(row._mapping)
                        ingredient['current_stock'] = float(ingredient.get('current_stock', 0))
                        ingredient['min_stock_level'] = float(ingredient.get('min_stock_level', 0))
                        return ingredient
                return ingredient_data
        except Exception as e:
            print(f"❌ Ошибка при создании ингредиента: {e}")
            raise

    def update_ingredient(self, ingredient_id: int, ingredient_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обновить ингредиент"""
        try:
            with self.engine.connect() as conn:
                # Преобразуем float в строки для SQLite
                for field in ['current_stock', 'min_stock_level']:
                    if field in ingredient_data:
                        ingredient_data[field] = float(ingredient_data[field])

                set_parts = []
                params = {"id": ingredient_id}

                for key, value in ingredient_data.items():
                    if value is not None and key != 'id':
                        set_parts.append(f"{key} = :{key}")
                        params[key] = value

                if not set_parts:
                    return None

                query = f"UPDATE ingredients SET {', '.join(set_parts)} WHERE id = :id"
                result = conn.execute(text(query), params)
                conn.commit()

                if result.rowcount > 0:
                    # Возвращаем обновленный ингредиент
                    with self.engine.connect() as conn2:
                        result2 = conn2.execute(
                            text("SELECT * FROM ingredients WHERE id = :id"),
                            {"id": ingredient_id}
                        )
                        row = result2.fetchone()
                        if row:
                            ingredient = dict(row._mapping)
                            ingredient['current_stock'] = float(ingredient.get('current_stock', 0))
                            ingredient['min_stock_level'] = float(ingredient.get('min_stock_level', 0))
                            return ingredient
                return None
        except Exception as e:
            print(f"❌ Ошибка при обновлении ингредиента: {e}")
            raise

    def delete_ingredient(self, ingredient_id: int) -> bool:
        """Удалить ингредиент"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("DELETE FROM ingredients WHERE id = :id"),
                    {"id": ingredient_id}
                )
                conn.commit()
                return result.rowcount > 0
        except Exception as e:
            print(f"❌ Ошибка при удалении ингредиента: {e}")
            return False

# Создаем глобальный экземпляр
db = Database()