from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import inspect, text

from database import db


def _normalize_list(items: Optional[List[str]]) -> Tuple[str, ...]:
    if not items:
        return tuple()
    normalized = []
    for item in items:
        if item:
            normalized.append(item.strip().lower())
    return tuple(sorted(normalized))


class MenuService:
    def __init__(self, cache_ttl_seconds: int = 120):
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self.cache: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
        self._ensure_menu_table()

    def _table_exists(self, table_name: str) -> bool:
        try:
            return table_name in inspect(db.engine).get_table_names()
        except Exception:
            return False

    @property
    def _dialect(self) -> str:
        return db.engine.dialect.name

    def _ensure_menu_table(self) -> None:
        if db.engine is None:
            return

        if self._dialect == "sqlite":
            create_sql = """
                CREATE TABLE IF NOT EXISTS menu_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dish_id INTEGER NOT NULL UNIQUE,
                    is_hit BOOLEAN DEFAULT 0,
                    is_new BOOLEAN DEFAULT 0,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (dish_id) REFERENCES dishes(id)
                )
            """
        else:
            create_sql = """
                CREATE TABLE IF NOT EXISTS menu_items (
                    id SERIAL PRIMARY KEY,
                    dish_id INTEGER NOT NULL UNIQUE,
                    is_hit BOOLEAN DEFAULT FALSE,
                    is_new BOOLEAN DEFAULT FALSE,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (dish_id) REFERENCES dishes(id)
                )
            """

        with db.engine.begin() as conn:
            conn.execute(text(create_sql))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_menu_items_dish_id
                ON menu_items(dish_id)
            """))

    def _get_last_updated(self, conn) -> Optional[datetime]:
        result = conn.execute(text("SELECT MAX(updated_at) as updated_at FROM menu_items"))
        row = result.fetchone()
        if row and row.updated_at:
            if isinstance(row.updated_at, datetime):
                return row.updated_at
            try:
                return datetime.fromisoformat(str(row.updated_at))
            except Exception:
                return None
        return None

    def _get_selects(self) -> Dict[str, str]:
        if self._dialect == "sqlite":
            return {
                "tags": "GROUP_CONCAT(DISTINCT dt.name)",
                "ingredients": "GROUP_CONCAT(DISTINCT ing.name)",
            }

        return {
            "tags": "STRING_AGG(DISTINCT dt.name, ',')",
            "ingredients": "STRING_AGG(DISTINCT ing.name, ',')",
        }

    def _query_menu(
        self,
        conn,
        include_tags: Tuple[str, ...],
        exclude_allergens: Tuple[str, ...],
        limit: int,
        sort_by: str,
    ) -> List[Dict[str, Any]]:
        selects = self._get_selects()

        query = f"""
            SELECT
                d.id,
                d.name,
                c.name AS category_name,
                {selects['tags']} AS tags,
                {selects['ingredients']} AS ingredients,
                COALESCE(mi.is_hit, 0) AS is_hit,
                COALESCE(mi.is_new, 0) AS is_new,
                mi.updated_at AS updated_at
            FROM dishes d
            LEFT JOIN visit_categories c ON d.category_id = c.id
            LEFT JOIN dish_tag_map dtm ON d.id = dtm.dish_id
            LEFT JOIN dish_tags dt ON dtm.tag_id = dt.id
            LEFT JOIN dish_ingredients di ON d.id = di.dish_id
            LEFT JOIN ingredients ing ON di.ingredient_id = ing.id
            LEFT JOIN menu_items mi ON mi.dish_id = d.id
            WHERE d.is_available = 1
        """

        params: Dict[str, Any] = {}

        if include_tags:
            tag_placeholders = []
            for idx, tag in enumerate(include_tags):
                param_name = f"tag_{idx}"
                tag_placeholders.append(f":{param_name}")
                params[param_name] = tag

            query += f"""
                AND EXISTS (
                    SELECT 1 FROM dish_tag_map dtm2
                    JOIN dish_tags dt2 ON dtm2.tag_id = dt2.id
                    WHERE dtm2.dish_id = d.id AND LOWER(dt2.name) IN ({', '.join(tag_placeholders)})
                )
            """

        if exclude_allergens:
            allergen_placeholders = []
            for idx, allergen in enumerate(exclude_allergens):
                param_name = f"allergen_{idx}"
                allergen_placeholders.append(f":{param_name}")
                params[param_name] = allergen

            query += f"""
                AND d.id NOT IN (
                    SELECT di2.dish_id
                    FROM dish_ingredients di2
                    JOIN ingredients ing2 ON di2.ingredient_id = ing2.id
                    WHERE LOWER(ing2.name) IN ({', '.join(allergen_placeholders)})
                )
            """

        query += """
            GROUP BY d.id, d.name, c.name, mi.is_hit, mi.is_new, mi.updated_at
        """

        if sort_by == "hits":
            order_clause = "COALESCE(mi.is_hit, 0) DESC, d.name"
        elif sort_by == "new":
            order_clause = "COALESCE(mi.is_new, 0) DESC, d.name"
        else:
            order_clause = "d.name"

        query += f" ORDER BY {order_clause} LIMIT :limit"
        params["limit"] = limit

        result = conn.execute(text(query), params)

        items = []
        for row in result.fetchall():
            tags = []
            ingredients = []

            if row.tags:
                tags = [tag.strip() for tag in str(row.tags).split(',') if tag.strip()]
            if row.ingredients:
                ingredients = [ing.strip() for ing in str(row.ingredients).split(',') if ing.strip()]

            items.append({
                "id": row.id,
                "name": row.name,
                "category": row.category_name,
                "tags": tags,
                "ingredients": ingredients,
                "is_hit": bool(row.is_hit),
                "is_new": bool(row.is_new),
            })

        return items

    def get_compact_menu(
        self,
        include_tags: Optional[List[str]] = None,
        exclude_allergens: Optional[List[str]] = None,
        limit: int = 20,
        sort_by: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if limit < 1:
            raise ValueError("Лимит должен быть положительным")

        normalized_tags = _normalize_list(include_tags)
        normalized_allergens = _normalize_list(exclude_allergens)
        normalized_sort = (sort_by or "").lower() or "default"

        if normalized_sort not in ("default", "hits", "new"):
            raise ValueError("Недопустимое значение сортировки")

        cache_key = (normalized_tags, normalized_allergens, limit, normalized_sort)
        now = datetime.utcnow()
        cached = self.cache.get(cache_key)

        with db.engine.connect() as conn:
            last_updated = self._get_last_updated(conn)

            if cached and cached["expires_at"] > now and cached["last_updated"] == last_updated:
                return cached["data"]

            items = self._query_menu(
                conn=conn,
                include_tags=normalized_tags,
                exclude_allergens=normalized_allergens,
                limit=limit,
                sort_by=normalized_sort,
            )

            self.cache[cache_key] = {
                "expires_at": now + self.cache_ttl,
                "last_updated": last_updated,
                "data": items,
            }

            return items


menu_service = MenuService()

menu_router = APIRouter(
    prefix="/menu",
    tags=["Меню"],
    responses={404: {"description": "Не найдено"}}
)


@menu_router.get("/compact", summary="Компактный список блюд")
async def get_compact_menu(
    tags: Optional[List[str]] = Query(None, alias="tag"),
    exclude_allergens: Optional[List[str]] = Query(None, alias="exclude_allergen"),
    limit: int = Query(20, ge=1, le=100),
    sort_by: Optional[str] = Query(None, description="Допустимые значения: hits, new"),
):
    try:
        items = menu_service.get_compact_menu(
            include_tags=tags,
            exclude_allergens=exclude_allergens,
            limit=limit,
            sort_by=sort_by,
        )
        return {
            "success": True,
            "count": len(items),
            "items": items,
            "filters": {
                "tags": tags or [],
                "exclude_allergens": exclude_allergens or [],
                "limit": limit,
                "sort_by": sort_by or "default"
            }
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении меню: {exc}")
