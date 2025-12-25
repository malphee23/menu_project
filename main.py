# python main.py - для запуска локального сайта в терминале PyCharm или cmd
# http://127.0.0.1:8000/docs - интерактивная документация
# Ip и порт будет показан в терминале или cmd
# . venv/Scripts/activate

# from gigachat import GigaChat
import json
import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
import uvicorn
from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import text
import urllib3

from mobile import mobile_router
from admin import admin_router
from sofia_modules import orders_router, payments_router, reviews_router, kitchen_router
from auth import auth_router
from database import db

from storage import *

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

app = FastAPI(
    title="Restaurant API",
    description="API for restaurant service",
)

class GigaChatClient:
    def __init__(self, credentials: str):
        self.credentials = credentials
        self.access_token = None
        self._get_token()

    def _get_token(self):
        url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        payload = {"scope": "GIGACHAT_API_PERS"}
        headers = {
            "Authorization": f"Basic {self.credentials}",
            "RqUID": str(uuid.uuid4()),
            "Content-Type": "application/x-www-form-urlencoded"
        }
        response = requests.post(url, data=payload, headers=headers, verify=False)
        response.raise_for_status()
        self.access_token = response.json()["access_token"]

    def send_message(self, messages: list):
        url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "GigaChat",
            "messages": messages
        }
        response = requests.post(url, json=payload, headers=headers, verify=False)
        if response.status_code == 401:
            self._get_token()
            headers["Authorization"] = f"Bearer {self.access_token}"
            response = requests.post(url, json=payload, headers=headers, verify=False)

        response.raise_for_status()
        return response.json()

GIGA_CLIENT = GigaChatClient(credentials=os.getenv("GIGACHAT_CREDENTIALS"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router)
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


class RecommendationRequest(BaseModel):
    tags: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    restrictions: List[str] = Field(default_factory=list)


class RecommendationItem(BaseModel):
    id: int
    name: str
    score: float = Field(ge=0, le=1)


class RecommendationResponse(BaseModel):
    items: List[RecommendationItem]


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

@app.post("/gigachat/")
async def chat_with_gigachat(user_message: str):
    try:
        messages = [{"role": "user", "content": user_message}]
        response = GIGA_CLIENT.send_message(messages)
        return {
            "response": response["choices"][0]["message"]["content"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GigaChat error: {str(e)}")

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


def build_recommendation_prompt(context_dishes: List[Dict[str, Any]], request: RecommendationRequest) -> Dict[str, Any]:
    system_prompt = (
        "Ты помощник ресторана. Выбирай только из предложенных блюд. "
        "Верни строгий JSON без текста: {\"items\":[{\"id\":...,\"name\":...,\"score\":0..1}]}"
    )

    user_parts = ["Доступные блюда:"]
    for dish in context_dishes:
        user_parts.append(
            f"- id={dish['id']}; name={dish['name']}; "
            f"tags={dish.get('tags')}; ingredients={dish.get('ingredients')}"
        )

    user_parts.append(
        "Запрос пользователя: "
        f"теги={', '.join(request.tags) or 'нет'}, "
        f"аллергии={', '.join(request.allergies) or 'нет'}, "
        f"ограничения={', '.join(request.restrictions) or 'нет'}"
    )

    return {
        "system": system_prompt,
        "user": "\n".join(user_parts)
    }


def parse_recommendation_response(raw_text: str) -> RecommendationResponse:
    try:
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        cleaned = match.group(0) if match else raw_text
        cleaned = re.sub(r"^[^\{]*", "", cleaned).strip()
        data = json.loads(cleaned)
        return RecommendationResponse(**data)
    except (json.JSONDecodeError, ValidationError) as e:
        raise HTTPException(status_code=502, detail=f"Invalid LLM response: {e}")


@app.post("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    tags = _normalize_list(request.tags)
    allergies = _normalize_list(request.allergies)
    restrictions = _normalize_list(request.restrictions)

    dishes = fetch_relevant_dishes(tags, allergies, restrictions)
    if not dishes:
        raise HTTPException(status_code=404, detail="Нет доступных блюд для рекомендаций")

    prompts = build_recommendation_prompt(dishes, RecommendationRequest(tags=tags, allergies=allergies, restrictions=restrictions))

    messages = [
        {"role": "system", "content": prompts["system"]},
        {"role": "user", "content": prompts["user"]},
    ]

    try:
        response = GIGA_CLIENT.send_message(messages)
        content = response["choices"][0]["message"]["content"]
        return parse_recommendation_response(content)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GigaChat error: {str(e)}")

if __name__ == "__main__":
    app_host = os.getenv("APP_HOST", "127.0.0.1")
    app_port = int(os.getenv("APP_PORT", "8000"))
    uvicorn.run("main:app", host=app_host, port=app_port, reload=True)
