# admin.py
from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException, Query, APIRouter
from pydantic import BaseModel
from database import db

# Создаем роутер для админских эндпоинтов
admin_router = APIRouter(
    prefix="/admin",
    tags=["Админ"],
    responses={404: {"description": "Не найдено"}}
)


# ========== МОДЕЛИ (только те, что используются в админских эндпоинтах) ==========

class UserFromDB(BaseModel):
    """Модель пользователя из БД"""
    id: Optional[int] = None
    login: Optional[str] = None
    birth_date: Optional[str] = None
    diet_type: Optional[str] = None
    meal_style: Optional[str] = None

    class Config:
        orm_mode = True


class Category(BaseModel):
    """Модель категории"""
    id: Optional[int] = None
    name: str
    description: Optional[str] = None

    class Config:
        orm_mode = True


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


# ========== ПОЛЬЗОВАТЕЛИ ==========

@admin_router.get("/users", response_model=List[UserFromDB])
async def get_all_users():
    try:
        users = db.get_all_users()
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


@admin_router.delete("/users/{user_id}")
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


@admin_router.get("/users/count")
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

@admin_router.get("/dishes", response_model=List[DishResponse])
async def get_all_dishes(
        category_id: Optional[int] = Query(None, description="Фильтр по категории"),
        available_only: bool = Query(True, description="Только доступные блюда")
):
    try:
        dishes = db.get_all_dishes(category_id=category_id, available_only=available_only)
        return dishes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/dishes/{dish_id}", response_model=DishResponse)
async def get_dish(dish_id: int):
    dish = db.get_dish_by_id(dish_id)
    if not dish:
        raise HTTPException(status_code=404, detail="Блюдо не найдено")
    return dish


@admin_router.post("/dishes", response_model=DishResponse)
async def create_dish(dish: DishCreate):
    try:
        created_dish = db.create_dish(dish.dict())
        return created_dish
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@admin_router.put("/dishes/{dish_id}", response_model=DishResponse)
async def update_dish(dish_id: int, dish: DishUpdate):
    try:
        update_data = {k: v for k, v in dish.dict().items() if v is not None}
        updated_dish = db.update_dish(dish_id, update_data)
        if not updated_dish:
            raise HTTPException(status_code=404, detail="Блюдо не найдено")
        return updated_dish
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@admin_router.delete("/dishes/{dish_id}")
async def delete_dish(dish_id: int):
    success = db.delete_dish(dish_id)
    if not success:
        raise HTTPException(status_code=404, detail="Блюдо не найдено")
    return {"success": True, "message": f"Блюдо с ID {dish_id} удалено"}


# ========== НАПИТКИ ==========

@admin_router.get("/bar-items", response_model=List[BarItemResponse])
async def get_all_bar_items():
    try:
        items = db.get_all_bar_items()
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/bar-items/{item_id}", response_model=BarItemResponse)
async def get_bar_item(item_id: int):
    item = db.get_bar_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Напиток не найден")
    return item


@admin_router.post("/bar-items", response_model=BarItemResponse)
async def create_bar_item(item: BarItemCreate):
    try:
        created_item = db.create_bar_item(item.dict())
        return created_item
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@admin_router.put("/bar-items/{item_id}", response_model=BarItemResponse)
async def update_bar_item(item_id: int, item: BarItemUpdate):
    try:
        update_data = {k: v for k, v in item.dict().items() if v is not None}
        updated_item = db.update_bar_item(item_id, update_data)
        if not updated_item:
            raise HTTPException(status_code=404, detail="Напиток не найден")
        return updated_item
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@admin_router.delete("/bar-items/{item_id}")
async def delete_bar_item(item_id: int):
    success = db.delete_bar_item(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Напиток не найден")
    return {"success": True, "message": f"Напиток с ID {item_id} удален"}


# ========== КАТЕГОРИИ ==========

@admin_router.get("/categories", response_model=List[Category])
async def get_all_categories():
    try:
        categories = db.get_all_categories()
        return categories
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/visit_categories")
async def get_visit_categories():
    """Получить категории посещений (для фронтенда)"""
    try:
        categories = db.get_all_categories()
        return categories
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/menu/all")
async def get_complete_menu():
    """Получить полное меню (блюда + напитки)"""
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

@admin_router.get("/ingredients", response_model=List[IngredientResponse])
async def get_all_ingredients():
    """Получить все ингредиенты"""
    try:
        ingredients = db.get_all_ingredients()
        return ingredients
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.post("/ingredients", response_model=IngredientResponse)
async def create_ingredient(ingredient: IngredientCreate):
    """Создать новый ингредиент"""
    try:
        created_ingredient = db.create_ingredient(ingredient.dict())
        return created_ingredient
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@admin_router.put("/ingredients/{ingredient_id}")
async def update_ingredient(ingredient_id: int, ingredient: IngredientUpdate):
    """Обновить ингредиент"""
    try:
        update_data = {k: v for k, v in ingredient.dict().items() if v is not None}
        updated_ingredient = db.update_ingredient(ingredient_id, update_data)
        if not updated_ingredient:
            raise HTTPException(status_code=404, detail="Ингредиент не найден")
        return updated_ingredient
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@admin_router.delete("/ingredients/{ingredient_id}")
async def delete_ingredient(ingredient_id: int):
    """Удалить ингредиент"""
    success = db.delete_ingredient(ingredient_id)
    if not success:
        raise HTTPException(status_code=404, detail="Ингредиент не найден")
    return {"success": True, "message": f"Ингредиент с ID {ingredient_id} удален"}


# ========== СИСТЕМНЫЕ ЭНДПОИНТЫ ==========

@admin_router.get("/db/health")
async def db_health_check():
    try:
        tables = db.get_all_tables()
        has_users_table = 'users' in tables

        return {
            "status": "connected",
            "database": "restaurant.db",
            "has_users_table": has_users_table,
            "tables_count": len(tables),
            "tables": tables,
            "message": "Подключение к базе данных успешно"
        }
    except Exception as e:
        return {
            "status": "error",
            "database": "restaurant.db",
            "error": str(e),
            "message": "Ошибка подключения к базе данных"
        }


# ========== ФУНКЦИИ ДЛЯ ПЕРСОНАЛА (также админские) ==========

@admin_router.get("/submissions")
async def get_all_submissions():
    """Получить все заявки от посетителей"""
    from main import visitor_submissions, session_flags
    return {
        "submissions": visitor_submissions,
        "total": len(visitor_submissions),
        "active_sessions": len([f for f in session_flags.values() if f])
    }


@admin_router.get("/submissions/{table_number}")
async def get_table_submission(table_number: int):
    """Получить заявки по номеру стола"""
    from main import visitor_submissions, session_flags
    table_subs = [s for s in visitor_submissions if s["table_number"] == table_number]
    session_status = session_flags.get(table_number, False)

    return {
        "submissions": table_subs,
        "table_number": table_number,
        "session_active": session_status,
        "has_active_order": len(table_subs) > 0
    }


@admin_router.get("/tables/status")
async def get_tables_status():
    """Получить статус всех столов"""
    from main import visitor_submissions, session_flags
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


@admin_router.put("/complete/{table_number}")
async def mark_table_completed(table_number: int):
    """Отметить стол как обслуженный"""
    from main import visitor_submissions, session_flags
    global visitor_submissions

    # Обновляем глобальную переменную в main.py
    import main
    main.visitor_submissions = [
        s for s in main.visitor_submissions
        if s["table_number"] != table_number
    ]

    if table_number in main.session_flags:
        main.session_flags[table_number] = False

    return {
        "message": f"Столик {table_number} обслужен",
        "session_ended": True,
        "table_number": table_number
    }