from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid
from database import db
from sqlalchemy import text


class OrderCreate(BaseModel):
    user_id: int
    table_number: int
    dish_ids: List[int]


class PaymentRequest(BaseModel):
    order_id: str
    amount: float


class ReviewCreate(BaseModel):
    order_id: str
    rating: int  # 1–5
    comment: Optional[str] = None


class QRRequest(BaseModel):
    order_id: str


orders_router = APIRouter(prefix="/orders", tags=["Заказы"])
payments_router = APIRouter(prefix="/payments", tags=["Оплата"])
reviews_router = APIRouter(prefix="/reviews", tags=["Отзывы"])
kitchen_router = APIRouter(prefix="/kitchen", tags=["Кухня"])


def _table_exists(table_name: str) -> bool:
    try:
        inspector = db.engine
        from sqlalchemy import inspect
        inspector_obj = inspect(inspector)
        return table_name in inspector_obj.get_table_names()
    except:
        return False


def _column_exists(table_name: str, column_name: str) -> bool:
    try:
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = inspector.get_columns(table_name)
        return any(col['name'] == column_name for col in columns)
    except:
        return False


@orders_router.get("/inventory/check", summary="Проверить наличие блюд")
async def check_inventory(dish_ids: str):
    try:
        ids = [int(x.strip()) for x in dish_ids.split(",")]
    except:
        raise HTTPException(400, "dish_ids — список через запятую")

    result = {}

    if not _table_exists('dishes'):
        raise HTTPException(500, "Таблица dishes не найдена в БД")

    with db.engine.connect() as conn:
        for dish_id in ids:
            dish_result = conn.execute(
                text("SELECT id, name, is_available FROM dishes WHERE id = :dish_id"),
                {"dish_id": dish_id}
            )
            dish = dish_result.fetchone()

            if dish:
                is_available = bool(dish.is_available) if hasattr(dish, 'is_available') else True
                result[dish_id] = {
                    "В наличии": is_available,
                    "Название": dish.name,
                    "Остаток": "Есть" if is_available else "Нет"
                }
            else:
                result[dish_id] = {"В наличии": False, "Остаток": "Блюдо не найдено"}

    return result


@orders_router.post("/", summary="Создать заказ")
async def create_order(order: OrderCreate):
    if not _table_exists('users'):
        raise HTTPException(500, "Таблица users не найдена в БД")

    with db.engine.connect() as conn:
        if _column_exists('users', 'birth_date'):
            user_result = conn.execute(
                text("SELECT id, birth_date FROM users WHERE id = :user_id"),
                {"user_id": order.user_id}
            )
        else:
            user_result = conn.execute(
                text("SELECT id FROM users WHERE id = :user_id"),
                {"user_id": order.user_id}
            )

        user = user_result.fetchone()
        if not user:
            raise HTTPException(404, "Пользователь не найден")

        user_age = None
        if hasattr(user, 'birth_date') and user.birth_date:
            try:
                from datetime import date
                birth_date = datetime.strptime(user.birth_date, "%Y-%m-%d").date()
                today = date.today()
                user_age = today.year - birth_date.year - (
                            (today.month, today.day) < (birth_date.month, birth_date.day))
            except:
                user_age = None

        total_price = 0.0
        for dish_id in order.dish_ids:
            if _table_exists('dish_tag_map') and _table_exists('dish_tags'):
                dish_query = """
                    SELECT d.id, d.name, d.price, d.is_available, 
                           GROUP_CONCAT(DISTINCT dt.name) as tags
                    FROM dishes d
                    LEFT JOIN dish_tag_map dtm ON d.id = dtm.dish_id
                    LEFT JOIN dish_tags dt ON dtm.tag_id = dt.id
                    WHERE d.id = :dish_id
                """
            else:
                dish_query = "SELECT id, name, price, is_available FROM dishes WHERE id = :dish_id"

            dish_result = conn.execute(text(dish_query), {"dish_id": dish_id})
            dish = dish_result.fetchone()

            if not dish:
                raise HTTPException(404, f"Блюдо {dish_id} не найдено")

            is_available = getattr(dish, 'is_available', 1)
            if is_available == 0:
                raise HTTPException(400, f"Блюдо '{dish.name}' временно недоступно")

            if hasattr(dish, 'tags') and dish.tags and 'алкоголь' in dish.tags.lower():
                if user_age and user_age < 18:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Алкогольное блюдо '{dish.name}' запрещено несовершеннолетним"
                    )

            total_price += float(dish.price)

        order_id = str(uuid.uuid4())[:8]
        current_time = datetime.now().isoformat()

        if _column_exists('orders', 'status'):
            status_val = 'В обработке'
        else:
            status_val = 'новый'

        order_result = conn.execute(
            text("""
                INSERT INTO orders (user_id, table_number, created_at, status, total_price)
                VALUES (:user_id, :table_number, :created_at, :status, :total_price)
            """),
            {
                "user_id": order.user_id,
                "table_number": order.table_number,
                "created_at": current_time,
                "status": status_val,
                "total_price": total_price
            }
        )

        order_db_id = order_result.lastrowid

        if _table_exists('order_items'):
            for dish_id in order.dish_ids:
                conn.execute(
                    text("""
                        INSERT INTO order_items (order_id, dish_id)
                        VALUES (:order_id, :dish_id)
                    """),
                    {
                        "order_id": order_db_id,
                        "dish_id": dish_id
                    }
                )

        conn.commit()

        return {
            "order_id": order_id,
            "db_order_id": order_db_id,
            "status": status_val,
            "total_price": total_price,
            "message": "Заказ создан успешно"
        }


@orders_router.get("/bar-menu", summary="Меню бара")
async def bar_menu(user_id: int):
    if not _table_exists('bar_items'):
        raise HTTPException(404, "Меню бара не найдено")

    with db.engine.connect() as conn:
        if _column_exists('users', 'birth_date'):
            user_result = conn.execute(
                text("SELECT birth_date FROM users WHERE id = :user_id"),
                {"user_id": user_id}
            )
            user = user_result.fetchone()

            is_minor = False
            if user and hasattr(user, 'birth_date') and user.birth_date:
                try:
                    from datetime import date
                    birth_date = datetime.strptime(user.birth_date, "%Y-%m-%d").date()
                    today = date.today()
                    user_age = today.year - birth_date.year - (
                                (today.month, today.day) < (birth_date.month, birth_date.day))
                    is_minor = user_age < 18
                except:
                    is_minor = False
        else:
            is_minor = False

        if is_minor and _column_exists('bar_items', 'is_alcoholic'):
            query = """
                SELECT id, name, description, price, strength
                FROM bar_items 
                WHERE is_alcoholic = 0 AND is_available = 1
                ORDER BY name
            """
            message = "Алкоголь недоступен для несовершеннолетних"
        else:
            if _column_exists('bar_items', 'is_alcoholic'):
                query = """
                    SELECT id, name, description, price, strength,
                           CASE WHEN is_alcoholic = 1 THEN 'Алкогольный' ELSE 'Безалкогольный' END as type
                    FROM bar_items 
                    WHERE is_available = 1
                    ORDER BY is_alcoholic DESC, name
                """
            else:
                query = """
                    SELECT id, name, description, price, strength
                    FROM bar_items 
                    WHERE is_available = 1
                    ORDER BY name
                """
            message = "Меню бара"

        items_result = conn.execute(text(query))
        items = []
        for row in items_result:
            item = dict(row._mapping)
            item['price'] = float(item['price'])
            items.append(item)

        return {
            "Сообщение": message,
            "Напитки": items
        }


@orders_router.get("/{order_id}", summary="Получить информацию о заказе")
async def get_order(order_id: str):
    try:
        order_num_id = int(order_id)
    except:
        order_num_id = None

    if not _table_exists('orders'):
        raise HTTPException(404, "Заказы не найдены")

    with db.engine.connect() as conn:
        if order_num_id:
            if _table_exists('users'):
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
                order_result = conn.execute(
                    text("SELECT * FROM orders WHERE id = :id"),
                    {"id": order_num_id}
                )
        else:
            if _table_exists('users'):
                order_result = conn.execute(
                    text("""
                        SELECT o.*, u.login as user_login
                        FROM orders o
                        LEFT JOIN users u ON o.user_id = u.id
                        WHERE CAST(o.id as TEXT) = :order_id
                    """),
                    {"order_id": order_id}
                )
            else:
                order_result = conn.execute(
                    text("SELECT * FROM orders WHERE CAST(id as TEXT) = :order_id"),
                    {"order_id": order_id}
                )

        order = order_result.fetchone()
        if not order:
            raise HTTPException(404, "Заказ не найден")

        items = []
        total_price = 0.0

        if _table_exists('order_items'):
            items_query = """
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
            """

            if not _table_exists('bar_items'):
                items_query = """
                    SELECT 
                        'Блюдо' as type,
                        d.name as name,
                        d.price as price
                    FROM order_items oi
                    LEFT JOIN dishes d ON oi.dish_id = d.id
                    WHERE oi.order_id = :order_id AND oi.dish_id IS NOT NULL
                """

            items_result = conn.execute(text(items_query), {"order_id": order.id})

            for item in items_result:
                item_dict = dict(item._mapping)
                if 'price' in item_dict:
                    item_dict['price'] = float(item_dict['price'])
                    total_price += item_dict['price']
                items.append(item_dict)

        order_dict = dict(order._mapping)
        order_dict['total_price'] = float(order_dict.get('total_price', total_price))
        order_dict['items'] = items

        return order_dict


@kitchen_router.get("/orders/new", summary="Новые заказы для кухни")
async def get_new_orders_for_kitchen():
    if not _table_exists('orders'):
        return {"new_orders": [], "count": 0}

    with db.engine.connect() as conn:
        if _table_exists('users') and _table_exists('order_items'):
            query = """
                SELECT o.*, u.login as user_login,
                       COUNT(oi.id) as items_count
                FROM orders o
                LEFT JOIN users u ON o.user_id = u.id
                LEFT JOIN order_items oi ON o.id = oi.order_id
                WHERE o.status = 'В обработке' OR o.status = 'новый'
                GROUP BY o.id
                ORDER BY o.created_at
            """
        elif _table_exists('users'):
            query = """
                SELECT o.*, u.login as user_login,
                       0 as items_count
                FROM orders o
                LEFT JOIN users u ON o.user_id = u.id
                WHERE o.status = 'В обработке' OR o.status = 'новый'
                ORDER BY o.created_at
            """
        else:
            query = """
                SELECT o.*, '' as user_login,
                       0 as items_count
                FROM orders o
                WHERE o.status = 'В обработке' OR o.status = 'новый'
                ORDER BY o.created_at
            """

        result = conn.execute(text(query))
        orders = []
        for row in result:
            order = dict(row._mapping)
            order['total_price'] = float(order.get('total_price', 0))
            orders.append(order)

        return {
            "new_orders": orders,
            "count": len(orders)
        }


@kitchen_router.post("/orders/{order_id}/accept", summary="Принять заказ на кухне")
async def accept_order(order_id: str):
    try:
        order_num_id = int(order_id)
    except:
        order_num_id = None

    if not _table_exists('orders'):
        raise HTTPException(404, "Таблица orders не найдена")

    with db.engine.connect() as conn:
        if order_num_id:
            result = conn.execute(
                text("""
                    UPDATE orders 
                    SET status = 'Заказ принят'
                    WHERE id = :id AND (status = 'В обработке' OR status = 'новый')
                """),
                {"id": order_num_id}
            )
        else:
            result = conn.execute(
                text("""
                    UPDATE orders 
                    SET status = 'Заказ принят'
                    WHERE CAST(id as TEXT) = :order_id AND (status = 'В обработке' OR status = 'новый')
                """),
                {"order_id": order_id}
            )

        conn.commit()

        if result.rowcount > 0:
            return {"message": "Заказ принят на кухню"}
        else:
            raise HTTPException(400, "Заказ не найден или уже принят")


@payments_router.get("/qr/{order_id}", summary="Генерация QR-кода")
async def get_payment_qr(order_id: str):
    try:
        order_num_id = int(order_id)
    except:
        order_num_id = None

    if not _table_exists('orders'):
        raise HTTPException(404, "Заказ не найден")

    with db.engine.connect() as conn:
        if order_num_id:
            if _table_exists('users'):
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
                    text("SELECT id, total_price, status FROM orders WHERE id = :id"),
                    {"id": order_num_id}
                )
        else:
            if _table_exists('users'):
                result = conn.execute(
                    text("""
                        SELECT o.id, o.total_price, o.status, u.login
                        FROM orders o
                        LEFT JOIN users u ON o.user_id = u.id
                        WHERE CAST(o.id as TEXT) = :order_id
                    """),
                    {"order_id": order_id}
                )
            else:
                result = conn.execute(
                    text("SELECT id, total_price, status FROM orders WHERE CAST(id as TEXT) = :order_id"),
                    {"order_id": order_id}
                )

        order = result.fetchone()
        if not order:
            raise HTTPException(404, "Заказ не найден")

        status = getattr(order, 'status', '')
        if status in ['Оплачен', 'Выполнен']:
            raise HTTPException(400, "Заказ уже оплачен")

        amount = float(order.total_price or 0)

        payment_url = f"t.me/send?start=IVp8IUrb6VAZ={order_id}&amount={amount}"

        return {
            "order_id": order_id,
            "amount": amount,
            "payment_url": payment_url,
            "qr_data": payment_url,
            "status": status
        }


@payments_router.post("/pay", summary="Оплатить заказ")
async def pay(payment: PaymentRequest):
    try:
        order_num_id = int(payment.order_id)
    except:
        order_num_id = None

    if not _table_exists('orders'):
        raise HTTPException(404, "Заказ не найден")

    with db.engine.connect() as conn:
        if order_num_id:
            result = conn.execute(
                text("SELECT id, total_price, status FROM orders WHERE id = :id"),
                {"id": order_num_id}
            )
        else:
            result = conn.execute(
                text("SELECT id, total_price, status FROM orders WHERE CAST(id as TEXT) = :order_id"),
                {"order_id": payment.order_id}
            )

        order = result.fetchone()
        if not order:
            raise HTTPException(404, "Заказ не найден")

        status = getattr(order, 'status', '')
        if status == 'Оплачен':
            raise HTTPException(400, "Заказ уже оплачен")

        expected_amount = float(order.total_price or 0)
        if abs(payment.amount - expected_amount) > 0.01:
            raise HTTPException(400, f"Сумма не совпадает. Ожидалось: {expected_amount}")

        if order_num_id:
            conn.execute(
                text("UPDATE orders SET status = 'Оплачен' WHERE id = :id"),
                {"id": order_num_id}
            )
        else:
            conn.execute(
                text("UPDATE orders SET status = 'Оплачен' WHERE CAST(id as TEXT) = :order_id"),
                {"order_id": payment.order_id}
            )

        payment_id = str(uuid.uuid4())[:8]
        conn.commit()

        return {
            "success": True,
            "payment_id": payment_id,
            "message": "Оплата прошла успешно",
            "order_id": payment.order_id,
            "amount": payment.amount
        }


@reviews_router.post("/", summary="Оставить отзыв")
async def add_review(review: ReviewCreate):
    if not _table_exists('orders'):
        raise HTTPException(404, "Заказ не найден")

    with db.engine.connect() as conn:
        try:
            order_id_int = int(review.order_id)
            result = conn.execute(
                text("SELECT id, status FROM orders WHERE id = :id"),
                {"id": order_id_int}
            )
        except:
            result = conn.execute(
                text("SELECT id, status FROM orders WHERE CAST(id as TEXT) = :order_id"),
                {"order_id": review.order_id}
            )

        order = result.fetchone()
        if not order:
            raise HTTPException(404, "Заказ не найден")

        status = getattr(order, 'status', '')
        if status != 'Оплачен':
            raise HTTPException(400, "Можно оставить отзыв только после оплаты")

        if not (1 <= review.rating <= 5):
            raise HTTPException(400, "Рейтинг должен быть от 1 до 5")

        review_id = str(uuid.uuid4())[:8]

        return {
            "success": True,
            "message": "Отзыв добавлен",
            "review_id": review_id,
            "rating": review.rating,
            "comment": review.comment
        }