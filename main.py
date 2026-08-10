# python main.py - для запуска локального сайта в терминале PyCharm или cmd
# http://127.0.0.1:8000/docs - интерактивная документация
# Ip и порт будет показан в терминале или cmd
# . venv/Scripts/activate

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import uvicorn
from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
import urllib3

from mobile import mobile_router
from admin import admin_router
from menu import menu_router
from sofia_modules import orders_router, payments_router, reviews_router, kitchen_router
from auth import auth_router
from database import db

from storage import *
from embedding_service import dish_vector_store, periodic_embeddings_refresh
from gigachat_service import (
    GigaChatQuery,
    RecommendationRequest,
    RecommendationResponse,
    build_contextual_messages,
    build_recommendation_prompt,
    create_gigachat_client_from_env,
    request_recommendations,
)

from starlette.middleware.cors import CORSMiddleware

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

dotenv_path = (
    find_dotenv(usecwd=True)
    or find_dotenv("env", usecwd=True)
    or find_dotenv("env.example", usecwd=True)
)
if dotenv_path:
    load_dotenv(dotenv_path)
    print(f"Loaded .env from: {dotenv_path}")  # для отладки
else:
    print("No .env file found!")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Restaurant API",
    description="API for restaurant service",
)

try:
    GIGA_CLIENT = create_gigachat_client_from_env()
except RuntimeError as error:
    logger.warning("GigaChat client is disabled: %s", error)
    GIGA_CLIENT = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router)
app.include_router(menu_router)
app.include_router(mobile_router)
app.include_router(orders_router)
app.include_router(payments_router)
app.include_router(reviews_router)
app.include_router(kitchen_router)
app.include_router(auth_router)

class VisitPurpose(BaseModel):
    purpose: str

class TastePreferences(BaseModel):
    preferences: List[str]

class DietaryRestrictions(BaseModel):
    restrictions: List[str]
    allergies: List[str]

class VisitorData(BaseModel):
    table_number: int
    visit_purpose: VisitPurpose
    taste_preferences: Optional[TastePreferences] = None
    dietary_restrictions: Optional[DietaryRestrictions] = None
    people_count: int


def _normalize_list(values: List[str]) -> List[str]:
    return [v.strip() for v in values if v and v.strip()]


def fetch_relevant_dishes(tags: List[str], allergies: List[str], restrictions: List[str]) -> List[Dict[str, Any]]:
    if not db._table_exists('dishes'):
        return []

    with db.engine.connect() as conn:
        joins = []
        select_extra = []
        params: Dict[str, Any] = {}

        has_tag_tables = db._table_exists('dish_tag_map') and db._table_exists('dish_tags')
        has_ingredient_tables = db._table_exists('dish_ingredients') and db._table_exists('ingredients')

        if has_tag_tables:
            joins.append("""
                LEFT JOIN dish_tag_map dtm ON d.id = dtm.dish_id
                LEFT JOIN dish_tags dt ON dtm.tag_id = dt.id
            """)
            select_extra.append("GROUP_CONCAT(DISTINCT dt.name) AS tags")

        if has_ingredient_tables:
            joins.append("""
                LEFT JOIN dish_ingredients di ON d.id = di.dish_id
                LEFT JOIN ingredients i ON di.ingredient_id = i.id
            """)
            select_extra.append("GROUP_CONCAT(DISTINCT i.name) AS ingredients")

        base_select = ["d.id", "d.name", "d.description"]
        query = "SELECT " + ", ".join(base_select + select_extra) + "\nFROM dishes d\n" + "\n".join(joins)

        where_clauses = ["d.is_available = 1"]

        if has_tag_tables:
            like_clauses = []
            for idx, tag in enumerate(tags):
                like_clauses.append(f"(dt.name LIKE :tag{idx})")
                params[f"tag{idx}"] = f"%{tag}%"
            if like_clauses:
                where_clauses.append("(" + " OR ".join(like_clauses) + ")")

            restriction_clauses = []
            for idx, restriction in enumerate(restrictions):
                restriction_clauses.append(f"(dt.name NOT LIKE :restriction{idx})")
                params[f"restriction{idx}"] = f"%{restriction}%"
            if restriction_clauses:
                where_clauses.append(" AND ".join(restriction_clauses))

        if has_ingredient_tables:
            allergy_clauses = []
            for idx, allergy in enumerate(allergies):
                allergy_clauses.append(f"(i.name NOT LIKE :allergy{idx})")
                params[f"allergy{idx}"] = f"%{allergy}%"
            if allergy_clauses:
                where_clauses.append(" AND ".join(allergy_clauses))

        if where_clauses:
            query += "\nWHERE " + " AND ".join(where_clauses)

        query += "\nGROUP BY d.id, d.name, d.description"

        result = conn.execute(text(query), params)
        dishes = []
        for row in result.fetchall():
            mapping = row._mapping
            dishes.append(
                {
                    "id": mapping.get("id"),
                    "name": mapping.get("name"),
                    "description": mapping.get("description"),
                    "tags": mapping.get("tags", ""),
                    "ingredients": mapping.get("ingredients", ""),
                }
            )
        return dishes

# Сессии и заказы

@app.post("/gigachat/", response_model=RecommendationResponse)
async def chat_with_gigachat(query: GigaChatQuery):
    if GIGA_CLIENT is None:
        raise HTTPException(status_code=503, detail="GigaChat не настроен")

    messages = build_contextual_messages(query, dish_vector_store)
    return request_recommendations(GIGA_CLIENT, messages)

@app.post("/startflag/{table_number}", tags=["Сессии"])
def start_session(table_number: int):
    session_flags[table_number] = True
    return {
        "success": True,
        "message": f"Сессия для стола {table_number} начата",
        "table_number": table_number,
        "session_active": True
    }

@app.post("/stopflag/{table_number}", tags=["Сессии"])
def stop_session(table_number: int):
    session_flags[table_number] = False
    return {
        "success": True,
        "message": f"Сессия для стола {table_number} завершена",
        "table_number": table_number,
        "session_active": False
    }

@app.get("/checkflag/{table_number}", tags=["Сессии"])
def check_session(table_number: int):
    is_active = session_flags.get(table_number, False)
    return {
        "table_number": table_number,
        "session_active": is_active,
        "message": f"Сессия {'активна' if is_active else 'не активна'}"
    }

@app.post("/submit-visit-info", tags=["Клиент"])
async def submit_visit_info(data: VisitorData):
    if not session_flags.get(data.table_number, False):
        raise HTTPException(
            status_code=400,
            detail=f"Сессия для стола {data.table_number} не активна."
        )

    submission_id = str(uuid.uuid4())[:8]
    submission = {
        "id": submission_id,
        "table_number": data.table_number,
        "visit_purpose": data.visit_purpose.purpose,
        "taste_preferences": data.taste_preferences.preferences if data.taste_preferences else [],
        "allergies": data.dietary_restrictions.allergies if data.dietary_restrictions else [],
        "restrictions": data.dietary_restrictions.restrictions if data.dietary_restrictions else [],
        "people_count": data.people_count,
        "timestamp": datetime.now().isoformat(),
        "status": "новый"
    }

    visitor_submissions.append(submission)

    return {
        "success": True,
        "message": "Ваш заказ принят, ожидайте",
        "table_number": data.table_number,
        "order_id": submission_id
    }


@app.post("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    tags = _normalize_list(request.tags)
    allergies = _normalize_list(request.allergies)
    restrictions = _normalize_list(request.restrictions)

    dishes = fetch_relevant_dishes(tags, allergies, restrictions)
    if not dishes:
        raise HTTPException(status_code=404, detail="Нет доступных блюд для рекомендаций")

    prompts = build_recommendation_prompt(
        dishes, RecommendationRequest(tags=tags, allergies=allergies, restrictions=restrictions)
    )

    messages = [
        {"role": "system", "content": prompts["system"]},
        {"role": "user", "content": prompts["user"]},
    ]

    if GIGA_CLIENT is None:
        raise HTTPException(status_code=503, detail="GigaChat не настроен")

    try:
        return request_recommendations(GIGA_CLIENT, messages)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GigaChat error: {str(e)}")

if __name__ == "__main__":
    app_host = os.getenv("APP_HOST", "127.0.0.1")
    app_port = int(os.getenv("APP_PORT", "8000"))
    uvicorn.run("main:app", host=app_host, port=app_port, reload=True)
