# mobile.py
import sqlite3
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

mobile_router = APIRouter(
    prefix="/mobile",
    tags=["Мобильное приложение"],
    responses={404: {"description": "Не найдено"}}
)


# Модели для запросов
class GuestData(BaseModel):
    category: str
    allergies: List[str] = []
    restrictions: List[str] = []
    preferences: List[str] = []
    table_number: int


class OrderUpdate(BaseModel):
    order_id: int
    dish_ids: Optional[List[int]] = None
    bar_item_ids: Optional[List[int]] = None


class MobileGuestHandler:
    def complete_guest_session(self, table_number: int) -> Dict[str, Any]:
        """Завершить сессию гостя"""
        try:
            self.connect()
            cursor = self.conn.cursor()

            # Обновляем статус заказов
            cursor.execute('''
                UPDATE orders 
                SET status = 'завершен' 
                WHERE table_number = ? AND status = 'новый'
            ''', (table_number,))

            self.conn.commit()

            return {
                "success": True,
                "table_number": table_number,
                "message": f"Сессия для стола {table_number} завершена"
            }
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            return {
                "success": False,
                "error": str(e),
                "message": "Ошибка при завершении сессии"
            }
        finally:
            self.disconnect()

    def get_visit_categories(self) -> List[Dict[str, Any]]:
        """Получить категории посещений"""
        try:
            self.connect()
            cursor = self.conn.cursor()
            cursor.execute('SELECT id, name FROM visit_categories ORDER BY name')
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Ошибка при получении категорий: {e}")
            return []
        finally:
            self.disconnect()

    def __init__(self, db_path: str = "restaurant.db"):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """Подключение к базе данных"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def disconnect(self):
        """Отключение от базы данных"""
        if self.conn:
            self.conn.close()

    def create_guest_user(self,
                          category: str,
                          allergies: List[str],
                          restrictions: List[str],
                          preferences: List[str],
                          table_number: int) -> Dict[str, Any]:
        """
        Создание записи гостя в базе данных
        """
        try:
            self.connect()
            cursor = self.conn.cursor()

            # Проверяем существует ли стол
            cursor.execute('SELECT id FROM tables WHERE table_number = ?', (table_number,))
            table_exists = cursor.fetchone()

            if not table_exists:
                return {
                    "success": False,
                    "error": f"Стол №{table_number} не существует",
                    "message": "Указанный стол не найден в системе"
                }

            # Преобразуем списки в строки для хранения
            allergies_str = ", ".join(allergies) if allergies else "Нет аллергии"
            restrictions_str = ", ".join(restrictions) if restrictions else "Нет ограничений"
            preferences_str = ", ".join(preferences) if preferences else "Любое"

            # Генерируем уникальный временный логин для гостя
            guest_login = f"guest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Вставляем запись гостя
            cursor.execute('''
                INSERT INTO users (login, password_hash, birth_date, diet_type, meal_style)
                VALUES (?, ?, ?, ?, ?)
            ''', (guest_login, None, None, restrictions_str, allergies_str))

            user_id = cursor.lastrowid

            # Создаем заказ/посещение для гостя
            cursor.execute('''
                INSERT INTO orders (user_id, created_at, status, total_price, table_number)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, datetime.now(), 'новый', 0.0, table_number))

            order_id = cursor.lastrowid

            self.conn.commit()

            return {
                "success": True,
                "user_id": user_id,
                "order_id": order_id,
                "guest_login": guest_login,
                "message": "Данные гостя сохранены успешно",
                "data": {
                    "category": category,
                    "allergies": allergies_str,
                    "restrictions": restrictions_str,
                    "preferences": preferences_str,
                    "table_number": table_number
                }
            }

        except Exception as e:
            if self.conn:
                self.conn.rollback()
            return {
                "success": False,
                "error": str(e),
                "message": "Ошибка при сохранении данных гостя"
            }
        finally:
            self.disconnect()

    def get_guest_by_table(self, table_number: int) -> List[Dict[str, Any]]:
        """Получить информацию о гостях за столом"""
        try:
            self.connect()
            cursor = self.conn.cursor()

            cursor.execute('''
                SELECT u.*, o.created_at, o.status, o.id as order_id, o.total_price, o.id as order_id
                FROM users u
                LEFT JOIN orders o ON u.id = o.user_id
                WHERE o.table_number = ? AND u.login LIKE 'guest_%'
                ORDER BY o.created_at DESC
            ''', (table_number,))

            guests = []
            for row in cursor.fetchall():
                guests.append(dict(row))

            return guests

        except Exception as e:
            print(f"Ошибка при получении гостей: {e}")
            return []
        finally:
            self.disconnect()

    def update_guest_order(self, order_id: int, dish_ids: List[int] = None,
                           bar_item_ids: List[int] = None) -> Dict[str, Any]:
        """Обновить заказ гостя (добавить блюда/напитки)"""
        try:
            self.connect()
            cursor = self.conn.cursor()

            total_price = 0.0

            # Добавляем блюда в заказ
            if dish_ids:
                for dish_id in dish_ids:
                    # Получаем цену блюда
                    cursor.execute('SELECT price FROM dishes WHERE id = ? AND is_available = 1', (dish_id,))
                    dish_row = cursor.fetchone()
                    if dish_row:
                        dish_price = dish_row[0]

                        # Добавляем в order_items
                        cursor.execute('''
                            INSERT INTO order_items (order_id, dish_id, bar_item_id)
                            VALUES (?, ?, NULL)
                        ''', (order_id, dish_id))

                        total_price += dish_price

            # Добавляем напитки в заказ
            if bar_item_ids:
                for item_id in bar_item_ids:
                    # Получаем цену напитка
                    cursor.execute('SELECT price FROM bar_items WHERE id = ? AND is_available = 1', (item_id,))
                    item_row = cursor.fetchone()
                    if item_row:
                        item_price = item_row[0]

                        # Добавляем в order_items
                        cursor.execute('''
                            INSERT INTO order_items (order_id, dish_id, bar_item_id)
                            VALUES (?, NULL, ?)
                        ''', (order_id, item_id))

                        total_price += item_price

            # Обновляем общую стоимость заказа
            if total_price > 0:
                cursor.execute('''
                    UPDATE orders 
                    SET total_price = total_price + ? 
                    WHERE id = ?
                ''', (total_price, order_id))

            self.conn.commit()

            return {
                "success": True,
                "order_id": order_id,
                "total_added": total_price,
                "message": "Заказ обновлен успешно"
            }

        except Exception as e:
            if self.conn:
                self.conn.rollback()
            return {
                "success": False,
                "error": str(e),
                "message": "Ошибка при обновлении заказа"
            }
        finally:
            self.disconnect()

    def get_menu_dishes(self) -> List[Dict[str, Any]]:
        """Получить доступные блюда для меню"""
        try:
            self.connect()
            cursor = self.conn.cursor()

            cursor.execute('''
                SELECT d.*, c.name as category_name 
                FROM dishes d
                LEFT JOIN visit_categories c ON d.category_id = c.id
                WHERE d.is_available = 1
                ORDER BY d.name
            ''')

            dishes = [dict(row) for row in cursor.fetchall()]
            return dishes

        except Exception as e:
            print(f"Ошибка при получении блюд: {e}")
            return []
        finally:
            self.disconnect()

    def get_menu_drinks(self) -> List[Dict[str, Any]]:
        """Получить доступные напитки для меню"""
        try:
            self.connect()
            cursor = self.conn.cursor()

            cursor.execute('''
                SELECT * FROM bar_items 
                WHERE is_available = 1
                ORDER BY name
            ''')

            drinks = [dict(row) for row in cursor.fetchall()]
            return drinks

        except Exception as e:
            print(f"Ошибка при получении напитков: {e}")
            return []
        finally:
            self.disconnect()


# Создаем экземпляр обработчика
guest_handler = MobileGuestHandler()


@mobile_router.post("/guest/register")
async def register_guest(guest_data: GuestData):
    """Регистрация гостя (вход без аккаунта)"""
    result = guest_handler.create_guest_user(
        category=guest_data.category,
        allergies=guest_data.allergies,
        restrictions=guest_data.restrictions,
        preferences=guest_data.preferences,
        table_number=guest_data.table_number
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@mobile_router.get("/guest/table/{table_number}")
async def get_table_guests(table_number: int):
    """Получить информацию о гостях за столом"""
    guests = guest_handler.get_guest_by_table(table_number)
    return {
        "table_number": table_number,
        "guests_count": len(guests),
        "guests": guests
    }


@mobile_router.post("/guest/order/update")
async def update_guest_order(order_update: OrderUpdate):
    """Обновить заказ гостя (добавить выбранные блюда/напитки)"""
    result = guest_handler.update_guest_order(
        order_id=order_update.order_id,
        dish_ids=order_update.dish_ids,
        bar_item_ids=order_update.bar_item_ids
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@mobile_router.get("/menu/dishes")
async def get_menu_dishes():
    """Получить доступные блюда для меню"""
    dishes = guest_handler.get_menu_dishes()
    return {
        "success": True,
        "dishes": dishes,
        "count": len(dishes)
    }


@mobile_router.get("/menu/drinks")
async def get_menu_drinks():
    """Получить доступные напитки для меню"""
    drinks = guest_handler.get_menu_drinks()
    return {
        "success": True,
        "drinks": drinks,
        "count": len(drinks)
    }


@mobile_router.get("/menu/all")
async def get_full_menu():
    """Полное меню (блюда + напитки)"""
    dishes = guest_handler.get_menu_dishes()
    drinks = guest_handler.get_menu_drinks()

    return {
        "success": True,
        "dishes": dishes,
        "drinks": drinks,
        "total_dishes": len(dishes),
        "total_drinks": len(drinks),
        "total_items": len(dishes) + len(drinks)
    }


@mobile_router.post("/guest/table/{table_number}/complete")
async def complete_table_session(table_number: int):
    """Завершить сессию гостей за столом"""
    result = guest_handler.complete_guest_session(table_number)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@mobile_router.get("/categories")
async def get_categories():
    """Получить категории посещений"""
    categories = guest_handler.get_visit_categories()
    return {
        "success": True,
        "categories": categories,
        "count": len(categories)
    }