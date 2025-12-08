# sofia_modules.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid
import asyncio
from database import db
from sqlalchemy import text


# =============== Схемы ===============
class OrderCreate(BaseModel):
    user_id: int
    table_number: int
    dish_ids: List[int]  # Например: [7, 8, 23]


class PaymentRequest(BaseModel):
    order_id: str
    amount: float


class ReviewCreate(BaseModel):
    order_id: str
    rating: int  # 1–5
    comment: Optional[str] = None


class QRRequest(BaseModel):
    order_id: str


# =============== Роутеры ===============
orders_router = APIRouter(prefix="/orders", tags=["Заказы"])
payments_router = APIRouter(prefix="/payments", tags=["Оплата"])
reviews_router = APIRouter(prefix="/reviews", tags=["Отзывы"])
kitchen_router = APIRouter(prefix="/kitchen", tags=["Админка"])


# =============== Склад, автоматически обновляется при создании заказа ===============
@orders_router.get("/inventory/check", summary="Принимает список dish_ids. Возвращает, есть ли каждое блюдо в наличии")
async def check_inventory(dish_ids: str):
    try:
        ids = [int(x.strip()) for x in dish_ids.split(",")]
    except:
        raise HTTPException(400, "dish_ids — список через запятую")

    result = {}
    with db.engine.connect() as conn:
        for dish_id in ids:
            # Проверяем доступность блюда через ингредиенты
            # В реальном приложении здесь будет сложная логика проверки остатков
            dish = db.get_dish_by_id(dish_id)
            if dish:
                # Упрощенная проверка: блюдо доступно если is_available = 1
                result[dish_id] = {
                    "В наличии": bool(dish.get('is_available', 0)),
                    "Название": dish.get('name'),
                    "Остаток": "Есть" if dish.get('is_available') else "Нет"
                }
            else:
                result[dish_id] = {"В наличии": False, "Остаток": "Блюдо не найдено"}

    return result


# =============== Создание заказа ===============
@orders_router.post("/", summary="Клиент выбирает блюда, создает заказ")
async def create_order(order: OrderCreate):
    # Проверяем существование пользователя
    with db.engine.connect() as conn:
        user_result = conn.execute(
            text("SELECT id, birth_date FROM users WHERE id = :user_id"),
            {"user_id": order.user_id}
        )
        user = user_result.fetchone()

        if not user:
            raise HTTPException(404, "Пользователь не найден")

        # Проверяем возраст для алкогольных блюд
        user_age = None
        if user.birth_date:
            from datetime import date
            birth_date = datetime.strptime(user.birth_date, "%Y-%m-%d").date()
            today = date.today()
            user_age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

        # Проверяем каждое блюдо
        total_price = 0.0
        for dish_id in order.dish_ids:
            # Получаем информацию о блюде
            dish_result = conn.execute(
                text("""
                    SELECT d.id, d.name, d.price, d.is_available, 
                           GROUP_CONCAT(DISTINCT dt.name) as tags
                    FROM dishes d
                    LEFT JOIN dish_tag_map dtm ON d.id = dtm.dish_id
                    LEFT JOIN dish_tags dt ON dtm.tag_id = dt.id
                    WHERE d.id = :dish_id
                """),
                {"dish_id": dish_id}
            )
            dish = dish_result.fetchone()

            if not dish:
                raise HTTPException(404, f"Блюдо {dish_id} не найдено")

            if not dish.is_available:
                raise HTTPException(400, f"Блюдо '{dish.name}' временно недоступно")

            # Проверяем на алкоголь (упрощенно - по названию или тегу)
            if dish.tags and 'алкоголь' in dish.tags.lower():
                if user_age and user_age < 18:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Алкогольное блюдо '{dish.name}' запрещено несовершеннолетним"
                    )

            total_price += float(dish.price)

        # Создаем заказ в базе
        order_id = str(uuid.uuid4())[:8]
        current_time = datetime.now().isoformat()

        # Вставляем заказ
        order_result = conn.execute(
            text("""
                INSERT INTO orders (id, user_id, table_number, created_at, status, total_price)
                VALUES (:id, :user_id, :table_number, :created_at, :status, :total_price)
            """),
            {
                "id": int(order_id, 16) % 1000000,  # Генерируем числовой ID из UUID
                "user_id": order.user_id,
                "table_number": order.table_number,
                "created_at": current_time,
                "status": "В обработке",
                "total_price": total_price
            }
        )

        # Вставляем элементы заказа
        for dish_id in order.dish_ids:
            conn.execute(
                text("""
                    INSERT INTO order_items (order_id, dish_id)
                    VALUES (:order_id, :dish_id)
                """),
                {
                    "order_id": order_result.lastrowid,
                    "dish_id": dish_id
                }
            )

        conn.commit()

        return {
            "order_id": order_id,
            "status": "В обработке",
            "total_price": total_price,
            "message": "Заказ создан успешно"
        }


# =============== Бар + возраст ===============
@orders_router.get("/bar-menu", summary="Выбор алкоголя, если клиент перешел на эту вкладку")
async def bar_menu(user_id: int):
    # Проверяем возраст пользователя
    with db.engine.connect() as conn:
        user_result = conn.execute(
            text("SELECT birth_date FROM users WHERE id = :user_id"),
            {"user_id": user_id}
        )
        user = user_result.fetchone()

        if not user:
            raise HTTPException(404, "Пользователь не найден")

        is_minor = False
        if user.birth_date:
            from datetime import date
            birth_date = datetime.strptime(user.birth_date, "%Y-%m-%d").date()
            today = date.today()
            user_age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            is_minor = user_age < 18

        # Получаем алкогольные напитки
        if is_minor:
            # Для несовершеннолетних показываем только безалкогольные
            items_result = conn.execute(
                text("""
                    SELECT id, name, description, price, strength
                    FROM bar_items 
                    WHERE is_alcoholic = 0 AND is_available = 1
                    ORDER BY name
                """)
            )
            message = "Алкоголь недоступен для несовершеннолетних"
        else:
            # Для совершеннолетних показываем все напитки
            items_result = conn.execute(
                text("""
                    SELECT id, name, description, price, strength,
                           CASE WHEN is_alcoholic = 1 THEN 'Алкогольный' ELSE 'Безалкогольный' END as type
                    FROM bar_items 
                    WHERE is_available = 1
                    ORDER BY is_alcoholic DESC, name
                """)
            )
            message = "Меню бара"

        items = []
        for row in items_result:
            item = dict(row._mapping)
            item['price'] = float(item['price'])
            items.append(item)

        return {
            "Сообщение": message,
            "Напитки": items
        }


# =============== Заказы ===============
@orders_router.get("/{order_id}", summary="Клиент получает информацию о заказе")
async def get_order(order_id: str):
    try:
        order_num_id = int(order_id, 16) % 1000000
    except:
        order_num_id = None

    with db.engine.connect() as conn:
        if order_num_id:
            order_result = conn.execute(
                text("""
                    SELECT o.*, u.login as user_login
                    FROM orders o
                    LEFT JOIN users u ON o.user_id = u.id
                    WHERE o.id = :id
                """),
                {"id": order_num_id}
            )
        else:
            # Если не числовой ID, ищем по другим полям
            order_result = conn.execute(
                text("""
                    SELECT o.*, u.login as user_login
                    FROM orders o
                    LEFT JOIN users u ON o.user_id = u.id
                    WHERE o.id = :id OR CAST(o.id as TEXT) = :order_id
                """),
                {"id": order_id if order_id.isdigit() else 0, "order_id": order_id}
            )

        order = order_result.fetchone()

        if not order:
            raise HTTPException(404, "Заказ не найден")

        # Получаем элементы заказа
        items_result = conn.execute(
            text("""
                SELECT 
                    CASE 
                        WHEN oi.dish_id IS NOT NULL THEN 'Блюдо'
                        WHEN oi.bar_item_id IS NOT NULL THEN 'Напиток'
                        ELSE 'Неизвестно'
                    END as type,
                    COALESCE(d.name, bi.name) as name,
                    COALESCE(d.price, bi.price) as price
                FROM order_items oi
                LEFT JOIN dishes d ON oi.dish_id = d.id
                LEFT JOIN bar_items bi ON oi.bar_item_id = bi.id
                WHERE oi.order_id = :order_id
            """),
            {"order_id": order.id}
        )

        items = []
        total_price = 0.0
        for item in items_result:
            item_dict = dict(item._mapping)
            item_dict['price'] = float(item_dict['price'])
            total_price += item_dict['price']
            items.append(item_dict)

        order_dict = dict(order._mapping)
        order_dict['total_price'] = float(order_dict.get('total_price', total_price))
        order_dict['items'] = items

        return order_dict


# =============== Получение списка новых заказов для админки ===============
@kitchen_router.get("/orders/new", summary="Повар заходит в админку, получает список новых заказов")
async def get_new_orders_for_kitchen():
    """
    Возвращает все заказы со статусом 'В обработке' (новые, не принятые)
    """
    with db.engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT o.*, u.login as user_login,
                       COUNT(oi.id) as items_count
                FROM orders o
                LEFT JOIN users u ON o.user_id = u.id
                LEFT JOIN order_items oi ON o.id = oi.order_id
                WHERE o.status = 'В обработке'
                GROUP BY o.id
                ORDER BY o.created_at
            """)
        )

        orders = []
        for row in result:
            order = dict(row._mapping)
            order['total_price'] = float(order.get('total_price', 0))
            orders.append(order)

        return {
            "new_orders": orders,
            "count": len(orders)
        }


# =============== Автоматическое уведомление повара о новом заказе ===============
@kitchen_router.get("/notifications/long-poll", summary="Автоматическое уведомление о новом заказе клиента повару")
async def admin_long_poll(timeout: int = 30):
    """
    Ждёт до 30 секунд появление нового заказа со статусом 'В обработке'.
    """
    start = datetime.now().timestamp()

    while (datetime.now().timestamp() - start) < timeout:
        with db.engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT COUNT(*) as count 
                    FROM orders 
                    WHERE status = 'В обработке'
                """)
            )
            count = result.fetchone().count

        if count > 0:
            return {
                "event": "Новый заказ",
                "message": f"Есть {count} новых заказов",
                "timestamp": datetime.now().isoformat()
            }

        await asyncio.sleep(2)

    return {"event": "Время ожидания истекло"}


# =============== Проверка заказа на принятость на кухню ===============
@kitchen_router.post("/orders/{order_id}/accept", summary="Повар нажимает принять")
async def accept_order(order_id: str):
    try:
        order_num_id = int(order_id) if order_id.isdigit() else None
    except:
        order_num_id = None

    with db.engine.connect() as conn:
        if order_num_id:
            result = conn.execute(
                text("""
                    UPDATE orders 
                    SET status = 'Заказ принят'
                    WHERE id = :id AND status = 'В обработке'
                """),
                {"id": order_num_id}
            )
        else:
            result = conn.execute(
                text("""
                    UPDATE orders 
                    SET status = 'Заказ принят'
                    WHERE id = :id AND status = 'В обработке'
                """),
                {"id": order_id if order_id.isdigit() else 0}
            )

        conn.commit()

        if result.rowcount > 0:
            return {"message": "Заказ принят на кухню"}
        else:
            raise HTTPException(400, "Заказ не найден или уже принят")


# =============== Уведомления (long-polling) ===============
@orders_router.get("/notifications/{order_id}", summary="Клиент получает уведомление, статус изменился")
async def wait_for_notification(order_id: str, timeout: int = 30):
    try:
        order_num_id = int(order_id) if order_id.isdigit() else None
    except:
        order_num_id = None

    with db.engine.connect() as conn:
        if order_num_id:
            result = conn.execute(
                text("SELECT status FROM orders WHERE id = :id"),
                {"id": order_num_id}
            )
        else:
            result = conn.execute(
                text("SELECT status FROM orders WHERE id = :id"),
                {"id": order_id if order_id.isdigit() else 0}
            )

        row = result.fetchone()
        if not row:
            raise HTTPException(404, "Заказ не найден")

        initial_status = row.status

    start = datetime.now().timestamp()

    while (datetime.now().timestamp() - start) < timeout:
        with db.engine.connect() as conn:
            if order_num_id:
                result = conn.execute(
                    text("SELECT status FROM orders WHERE id = :id"),
                    {"id": order_num_id}
                )
            else:
                result = conn.execute(
                    text("SELECT status FROM orders WHERE id = :id"),
                    {"id": order_id if order_id.isdigit() else 0}
                )

            row = result.fetchone()
            current_status = row.status if row else initial_status

            if current_status != initial_status:
                return {
                    "event": "Обновление статуса",
                    "order_id": order_id,
                    "old_status": initial_status,
                    "new_status": current_status
                }

        await asyncio.sleep(1)

    return {"event": "Время ожидания истекло"}


# =============== QR-код для оплаты ===============
@payments_router.get("/qr/{order_id}", summary="Генерация QR-кода")
async def get_payment_qr(order_id: str):
    try:
        order_num_id = int(order_id) if order_id.isdigit() else None
    except:
        order_num_id = None

    with db.engine.connect() as conn:
        if order_num_id:
            result = conn.execute(
                text("""
                    SELECT o.id, o.total_price, o.status, u.login
                    FROM orders o
                    LEFT JOIN users u ON o.user_id = u.id
                    WHERE o.id = :id
                """),
                {"id": order_num_id}
            )
        else:
            result = conn.execute(
                text("""
                    SELECT o.id, o.total_price, o.status, u.login
                    FROM orders o
                    LEFT JOIN users u ON o.user_id = u.id
                    WHERE o.id = :id
                """),
                {"id": order_id if order_id.isdigit() else 0}
            )

        order = result.fetchone()

        if not order:
            raise HTTPException(404, "Заказ не найден")

        if order.status in ['Оплачен', 'Выполнен']:
            raise HTTPException(400, "Заказ уже оплачен")

        amount = float(order.total_price or 0)

        # Генерируем "ссылку для оплаты"
        payment_url = f"t.me/send?start=IVp8IUrb6VAZ={order_id}&amount={amount}"

        return {
            "order_id": order_id,
            "amount": amount,
            "payment_url": payment_url,
            "qr_data": payment_url,
            "status": order.status
        }


# =============== Оплата ===============
@payments_router.post("/pay", summary="Клиент имитирует оплату")
async def pay(payment: PaymentRequest):
    try:
        order_num_id = int(payment.order_id) if payment.order_id.isdigit() else None
    except:
        order_num_id = None

    with db.engine.connect() as conn:
        # Проверяем существование заказа
        if order_num_id:
            result = conn.execute(
                text("SELECT id, total_price, status FROM orders WHERE id = :id"),
                {"id": order_num_id}
            )
        else:
            result = conn.execute(
                text("SELECT id, total_price, status FROM orders WHERE id = :id"),
                {"id": payment.order_id if payment.order_id.isdigit() else 0}
            )

        order = result.fetchone()

        if not order:
            raise HTTPException(404, "Заказ не найден")

        if order.status == 'Оплачен':
            raise HTTPException(400, "Заказ уже оплачен")

        # Проверяем сумму (допускаем небольшую погрешность)
        expected_amount = float(order.total_price or 0)
        if abs(payment.amount - expected_amount) > 0.01:
            raise HTTPException(400, f"Сумма не совпадает. Ожидалось: {expected_amount}")

        # Обновляем статус заказа
        if order_num_id:
            conn.execute(
                text("UPDATE orders SET status = 'Оплачен' WHERE id = :id"),
                {"id": order_num_id}
            )
        else:
            conn.execute(
                text("UPDATE orders SET status = 'Оплачен' WHERE id = :id"),
                {"id": payment.order_id if payment.order_id.isdigit() else 0}
            )

        # Создаем запись о платеже (упрощенно)
        payment_id = str(uuid.uuid4())[:8]

        conn.commit()

        return {
            "success": True,
            "payment_id": payment_id,
            "message": "Оплата прошла успешно",
            "order_id": payment.order_id,
            "amount": payment.amount
        }


# =============== Отзывы ===============
@reviews_router.post("/", summary="Написание отзыва")
async def add_review(review: ReviewCreate):
    try:
        order_num_id = int(review.order_id) if review.order_id.isdigit() else None
    except:
        order_num_id = None

    with db.engine.connect() as conn:
        # Проверяем заказ
        if order_num_id:
            result = conn.execute(
                text("SELECT id, status FROM orders WHERE id = :id"),
                {"id": order_num_id}
            )
        else:
            result = conn.execute(
                text("SELECT id, status FROM orders WHERE id = :id"),
                {"id": review.order_id if review.order_id.isdigit() else 0}
            )

        order = result.fetchone()

        if not order:
            raise HTTPException(404, "Заказ не найден")

        if order.status != 'Оплачен':
            raise HTTPException(400, "Можно оставить отзыв только после оплаты")

        if not (1 <= review.rating <= 5):
            raise HTTPException(400, "Рейтинг должен быть от 1 до 5")

        # В реальном приложении здесь была бы вставка в таблицу reviews
        # Так как у нас нет таблицы reviews, создадим заглушку
        review_id = str(uuid.uuid4())[:8]

        return {
            "success": True,
            "message": "Отзыв добавлен",
            "review_id": review_id,
            "rating": review.rating,
            "comment": review.comment
        }