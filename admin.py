from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException, Query, APIRouter
from pydantic import BaseModel

from storage import visitor_submissions, session_flags
from database import db

# Создаем роутер для админских эндпоинтов
admin_router = APIRouter(
    prefix="/admin",
    tags=["Админ"],
    responses={404: {"description": "Не найдено"}}
)

class AdminUserResponse(BaseModel):
    """Модель ответа для администратора"""
    id: int
    login: str
    role: str

    class Config:
        from_attributes = True

class AdminUserCreate(BaseModel):
    """Модель для создания пользователя системы"""
    login: str
    password: str  # Открытый пароль
    role: str = "waiter"  # По умолчанию официант

    model_config = {
        "json_schema_extra": {
            "example": {
                "login": "waiter1",
                "password": "password123",
                "role": "waiter"  # Возможные значения: "superuser", "cook", "waiter"
            }
        }
    }

class AdminUserUpdate(BaseModel):
    """Модель для обновления пользователя системы"""
    login: Optional[str] = None
    password: Optional[str] = None  # Опционально, только если меняем пароль
    role: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "login": "updated_waiter",
                "password": "newpassword456",  # Опционально
                "role": "waiter"  # Возможные значения: "superuser", "cook", "waiter"
            }
        }
    }

class UserFromDB(BaseModel):
    """Модель пользователя из БД"""
    id: Optional[int] = None
    login: Optional[str] = None
    birth_date: Optional[str] = None
    diet_type: Optional[str] = None
    meal_style: Optional[str] = None

    class Config:
        from_attributes = True


class Category(BaseModel):
    """Модель категории"""
    id: Optional[int] = None
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class DishCreate(BaseModel):
    """Модель для создания блюда"""
    name: str
    description: Optional[str] = None
    price: float
    category_id: Optional[int] = None
    is_available: bool = True


class DishResponse(BaseModel):
    """Модель ответа для блюда"""
    id: int
    name: str
    description: Optional[str] = None
    price: float
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    is_available: bool = True

    class Config:
        from_attributes = True


class DishUpdate(BaseModel):
    """Модель для обновления блюда"""
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category_id: Optional[int] = None
    is_available: Optional[bool] = None


class BarItemResponse(BaseModel):
    """Модель ответа для напитка"""
    id: int
    name: str
    description: Optional[str] = None
    price: float
    is_alcoholic: bool
    strength: Optional[float] = None
    is_available: bool

    class Config:
        from_attributes = True


class BarItemCreate(BaseModel):
    """Модель для создания напитка"""
    name: str
    description: Optional[str] = None
    price: float
    is_alcoholic: bool
    strength: Optional[float] = None
    is_available: bool = True


class BarItemUpdate(BaseModel):
    """Модель для обновления напитка"""
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    is_alcoholic: Optional[bool] = None
    strength: Optional[float] = None
    is_available: Optional[bool] = None


class IngredientResponse(BaseModel):
    """Модель ответа для ингредиента"""
    id: int
    name: str
    unit: str
    current_stock: float
    min_stock_level: float

    class Config:
        from_attributes = True


class IngredientCreate(BaseModel):
    """Модель для создания ингредиента"""
    name: str
    unit: str
    current_stock: float = 0.0
    min_stock_level: float = 0.0


class IngredientUpdate(BaseModel):
    """Модель для обновления ингредиента"""
    name: Optional[str] = None
    unit: Optional[str] = None
    current_stock: Optional[float] = None
    min_stock_level: Optional[float] = None


@admin_router.get("/admins",
                  response_model=List[AdminUserResponse],
                  summary="Получить всех администраторов",
                  description="Возвращает список всех администраторов системы без паролей")
async def get_all_admin_users():
    try:
        admins = db.get_all_admin_users()
        return admins
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


# 2. СОЗДАТЬ АДМИНА
@admin_router.post("/admins",
                   response_model=AdminUserResponse,
                   summary="Создать нового пользователя системы",
                   description="Создает нового пользователя с правами superuser/cook/waiter")
async def create_admin_user(admin: AdminUserCreate):
    try:
        # Базовая валидация
        if not admin.login or len(admin.login) < 3:
            raise HTTPException(status_code=400, detail="Логин должен быть не менее 3 символов")

        if not admin.password:
            raise HTTPException(status_code=400, detail="Пароль не может быть пустым")

        # Проверяем допустимые роли
        valid_roles = ["superuser", "cook", "waiter"]
        if admin.role not in valid_roles:
            raise HTTPException(
                status_code=400,
                detail=f"Роль должна быть одна из: {', '.join(valid_roles)}"
            )

        # Подготавливаем данные для БД
        admin_data = {
            "login": admin.login,
            "password_hash": admin.password,
            "role": admin.role
        }

        created_admin = db.create_admin_user(admin_data)
        return created_admin
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


# 3. ИЗМЕНИТЬ АДМИНА
@admin_router.put("/admins/{admin_id}",
                  response_model=AdminUserResponse,
                  summary="Обновить пользователя системы",
                  description="Обновляет логин, пароль и/или роль пользователя")
async def update_admin_user(admin_id: int, admin: AdminUserUpdate):
    try:
        # Проверяем, что есть хотя бы одно поле для обновления
        update_data = admin.model_dump(exclude_unset=True, exclude_none=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="Нет данных для обновления")

        # Если меняем логин, проверяем минимальную длину
        if 'login' in update_data and update_data['login'] and len(update_data['login']) < 3:
            raise HTTPException(status_code=400, detail="Логин должен быть не менее 3 символов")

        # Если меняем пароль, проверяем что он не пустой
        if 'password' in update_data and update_data['password']:
            password = update_data['password']
            if not password:
                raise HTTPException(status_code=400, detail="Пароль не может быть пустой строкой")
            if len(password) < 3:
                raise HTTPException(status_code=400, detail="Пароль должен быть не менее 3 символов")
            # Не удаляем пароль из update_data - метод БД его обработает

        # Если меняем роль, проверяем допустимые значения
        if 'role' in update_data and update_data['role']:
            valid_roles = ["superuser", "cook", "waiter"]
            if update_data['role'] not in valid_roles:
                raise HTTPException(
                    status_code=400,
                    detail=f"Роль должна быть одна из: {', '.join(valid_roles)}"
                )

        updated_admin = db.update_admin_user(admin_id, update_data)
        if not updated_admin:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        return updated_admin
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


# 4. УДАЛИТЬ АДМИНА
@admin_router.delete("/admins/{admin_id}",
                     summary="Удалить администратора",
                     description="Удаляет администратора по ID. Нельзя удалить последнего администратора.")
async def delete_admin_user(admin_id: int):
    try:
        success = db.delete_admin_user(admin_id)
        if not success:
            raise HTTPException(status_code=404, detail="Администратор не найден")

        return {
            "success": True,
            "message": f"Администратор с ID {admin_id} удален",
            "deleted_id": admin_id
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")

@admin_router.get("/users", response_model=List[UserFromDB], summary="Получить всех пользователей")
async def get_all_users():
    try:
        users = db.get_all_users()
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


@admin_router.delete("/users/{user_id}", summary="Удалить пользователя")
async def delete_user(user_id: int):
    try:
        success = db.delete_user(user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        return {
            "success": True,
            "message": f"Пользователь с ID {user_id} удален",
            "deleted_id": user_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


@admin_router.get("/users/count", summary="Получить число пользователей")
async def get_users_count():
    try:
        count = db.get_users_count()
        return {
            "success": True,
            "count": count,
            "message": f"В базе данных {count} пользователей"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


# ========== БЛЮДА ==========
@admin_router.get("/dishes", response_model=List[DishResponse], summary="Получить все блюда")
async def get_all_dishes(
        category_id: Optional[int] = Query(None, description="Фильтр по категории"),
        available_only: bool = Query(True, description="Только доступные блюда")
):
    try:
        dishes = db.get_all_dishes(category_id=category_id, available_only=available_only)
        return dishes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/dishes/{dish_id}", response_model=DishResponse, summary="Получить блюдо")
async def get_dish(dish_id: int):
    dish = db.get_dish_by_id(dish_id)
    if not dish:
        raise HTTPException(status_code=404, detail="Блюдо не найдено")
    return dish


@admin_router.post("/dishes", response_model=DishResponse, summary="Создать блюдо")
async def create_dish(dish: DishCreate):
    try:
        created_dish = db.create_dish(dish.model_dump())
        return created_dish
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@admin_router.put("/dishes/{dish_id}", response_model=DishResponse, summary="Изменить блюдо")
async def update_dish(dish_id: int, dish: DishUpdate):
    try:
        update_data = {k: v for k, v in dish.model_dump().items() if v is not None}
        updated_dish = db.update_dish(dish_id, update_data)
        if not updated_dish:
            raise HTTPException(status_code=404, detail="Блюдо не найдено")
        return updated_dish
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@admin_router.delete("/dishes/{dish_id}", summary="Удалить блюдо")
async def delete_dish(dish_id: int):
    success = db.delete_dish(dish_id)
    if not success:
        raise HTTPException(status_code=404, detail="Блюдо не найдено")
    return {"success": True, "message": f"Блюдо с ID {dish_id} удалено"}


# ========== НАПИТКИ ==========
@admin_router.get("/bar-items", response_model=List[BarItemResponse], summary="Получить все напитки")
async def get_all_bar_items():
    try:
        items = db.get_all_bar_items()
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/bar-items/{item_id}", response_model=BarItemResponse, summary="Получить напиток")
async def get_bar_item(item_id: int):
    item = db.get_bar_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Напиток не найден")
    return item


@admin_router.post("/bar-items", response_model=BarItemResponse, summary="Создать напиток")
async def create_bar_item(item: BarItemCreate):
    try:
        created_item = db.create_bar_item(item.model_dump())
        return created_item
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@admin_router.put("/bar-items/{item_id}", response_model=BarItemResponse, summary="Изменить напиток")
async def update_bar_item(item_id: int, item: BarItemUpdate):
    try:
        update_data = {k: v for k, v in item.model_dump().items() if v is not None}
        updated_item = db.update_bar_item(item_id, update_data)
        if not updated_item:
            raise HTTPException(status_code=404, detail="Напиток не найден")
        return updated_item
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@admin_router.delete("/bar-items/{item_id}", summary="Удалить напиток")
async def delete_bar_item(item_id: int):
    success = db.delete_bar_item(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Напиток не найден")
    return {"success": True, "message": f"Напиток с ID {item_id} удален"}


# ========== КАТЕГОРИИ ==========
@admin_router.get("/categories", response_model=List[Category], summary="Получить все категории")
async def get_all_categories():
    try:
        categories = db.get_all_categories()
        return categories
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/visit_categories", summary="Получить категорию")
async def get_visit_categories():
    try:
        categories = db.get_all_categories()
        return categories
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/menu/all", summary="Получить всё меню")
async def get_complete_menu():
    try:
        dishes = db.get_all_dishes()
        bar_items = db.get_all_bar_items()

        return {
            "dishes": dishes,
            "bar_items": bar_items,
            "total_dishes": len(dishes),
            "total_drinks": len(bar_items),
            "total_items": len(dishes) + len(bar_items)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== ИНГРЕДИЕНТЫ ==========
@admin_router.get("/ingredients", response_model=List[IngredientResponse], summary="Получить все ингредиенты")
async def get_all_ingredients():
    """Получить все ингредиенты"""
    try:
        ingredients = db.get_all_ingredients()
        return ingredients
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.post("/ingredients", response_model=IngredientResponse, summary="Создать ингредиент")
async def create_ingredient(ingredient: IngredientCreate):
    """Создать новый ингредиент"""
    try:
        created_ingredient = db.create_ingredient(ingredient.model_dump())
        return created_ingredient
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@admin_router.put("/ingredients/{ingredient_id}", summary="Изменить ингредиент")
async def update_ingredient(ingredient_id: int, ingredient: IngredientUpdate):
    """Обновить ингредиент"""
    try:
        update_data = {k: v for k, v in ingredient.model_dump().items() if v is not None}
        updated_ingredient = db.update_ingredient(ingredient_id, update_data)
        if not updated_ingredient:
            raise HTTPException(status_code=404, detail="Ингредиент не найден")
        return updated_ingredient
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@admin_router.delete("/ingredients/{ingredient_id}", summary="Удалить ингредиент")
async def delete_ingredient(ingredient_id: int):
    """Удалить ингредиент"""
    success = db.delete_ingredient(ingredient_id)
    if not success:
        raise HTTPException(status_code=404, detail="Ингредиент не найден")
    return {"success": True, "message": f"Ингредиент с ID {ingredient_id} удален"}


# ========== СИСТЕМНЫЕ ЭНДПОИНТЫ ==========
@admin_router.get("/db/health", summary="Проверка соединения с бд")
async def db_health_check():
    try:
        tables = db.get_all_tables()
        has_users_table = 'users' in tables

        # Получаем информацию о файле БД
        import os
        from database import db as db_instance

        db_info = {
            "status": "connected",
            "database_file": os.path.basename(db_instance.db_path),
            "database_path": db_instance.db_path,
            "file_size_kb": round(os.path.getsize(db_instance.db_path) / 1024, 1) if os.path.exists(
                db_instance.db_path) else 0,
            "has_users_table": has_users_table,
            "tables_count": len(tables),
            "tables": tables,
            "message": "Подключение к базе данных успешно"
        }

        # Добавляем статистику
        db_info["users_count"] = db.get_users_count()
        db_info["dishes_count"] = db.get_dishes_count()
        db_info["bar_items_count"] = db.get_bar_items_count()

        return db_info

    except Exception as e:
        return {
            "status": "error",
            "database": "unknown",
            "error": str(e),
            "message": "Ошибка подключения к базе данных"
        }


# ========== ФУНКЦИИ ДЛЯ ПЕРСОНАЛА ==========
@admin_router.get("/submissions", summary="Получить все заявки посетителей")
async def get_all_submissions():
    """Получить все заявки от посетителей"""
    return {
        "submissions": visitor_submissions,
        "total": len(visitor_submissions),
        "active_sessions": len([f for f in session_flags.values() if f])
    }


@admin_router.get("/submissions/{table_number}", summary="Получить заявку по номеру стола")
async def get_table_submission(table_number: int):
    """Получить заявки по номеру стола"""
    table_subs = [s for s in visitor_submissions if s["table_number"] == table_number]
    session_status = session_flags.get(table_number, False)

    return {
        "submissions": table_subs,
        "table_number": table_number,
        "session_active": session_status,
        "has_active_order": len(table_subs) > 0
    }


@admin_router.get("/tables/status", summary="Получить статус всех столов")
async def get_tables_status():
    """Получить статус всех столов"""
    statuses = []
    all_tables = set([s["table_number"] for s in visitor_submissions])

    for table_num in sorted(all_tables):
        table_orders = [s for s in visitor_submissions if s["table_number"] == table_num]
        session_active = session_flags.get(table_num, False)

        statuses.append({
            "table_number": table_num,
            "session_active": session_active,
            "orders_count": len(table_orders),
            "last_order": table_orders[-1]["timestamp"] if table_orders else None,
            "has_active_order": len(table_orders) > 0
        })

    return {
        "tables": statuses,
        "total_tables": len(all_tables),
        "active_sessions": len([f for f in session_flags.values() if f]),
        "total_orders": len(visitor_submissions)
    }


@admin_router.put("/complete/{table_number}", summary="Сделать стол обслуженным")
async def mark_table_completed(table_number: int):
    """Отметить стол как обслуженный"""
    # Удаляем заявки для этого стола
    global visitor_submissions
    visitor_submissions = [
        s for s in visitor_submissions
        if s["table_number"] != table_number
    ]

    # Завершаем сессию
    if table_number in session_flags:
        session_flags[table_number] = False

    return {
        "message": f"Столик {table_number} обслужен",
        "session_ended": True,
        "table_number": table_number
    }