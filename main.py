# python main.py - для запуска локального сайта в терминале PyCharm или cmd
# http://127.0.0.1:8000/docs - интерактивная документация
# Ip и порт будет показан в терминале или cmd
# . venv/Scripts/activate

# from gigachat import GigaChat
import json
import logging
import os
import uuid
from datetime import datetime
from typing import List, Optional

import requests
import uvicorn
import urllib3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError
from dotenv import load_dotenv, find_dotenv

from mobile import mobile_router
from admin import admin_router
from menu import menu_router
from sofia_modules import orders_router, payments_router, reviews_router, kitchen_router
from auth import auth_router

from storage import *
from embedding_service import dish_vector_store, periodic_embeddings_refresh

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

class RawRecommendationItem(BaseModel):
    id: int | str
    name: str
    score: float


class RawRecommendationResponse(BaseModel):
    items: List[RawRecommendationItem]


class RecommendationItem(BaseModel):
    id: int | str
    name: str
    score: float = Field(..., ge=0.0, le=1.0)


class RecommendationResponse(BaseModel):
    items: List[RecommendationItem]


def _normalize_recommendation_items(items: List[RawRecommendationItem]) -> List[RecommendationItem]:
    if not items:
        return []

    scores = [item.score for item in items]
    min_score = min(scores)
    max_score = max(scores)
    should_scale = min_score < 0 or max_score > 1

    normalized_items: List[RecommendationItem] = []
    for item in items:
        score = item.score
        if should_scale and max_score != min_score:
            score = (score - min_score) / (max_score - min_score)
        elif should_scale and max_score == min_score:
            score = 1.0 if score > 0 else 0.0

        score = max(0.0, min(1.0, score))
        normalized_items.append(RecommendationItem(id=item.id, name=item.name, score=score))

    normalized_items.sort(key=lambda x: x.score, reverse=True)
    return normalized_items

# Сессии и заказы

@app.post("/gigachat/", response_model=RecommendationResponse)
async def chat_with_gigachat(user_message: str):
    raw_payload = None
    try:
        top_k = max(1, min(query.top_k, 20))
        context_dishes = []
        if query.tags:
            query_vector = dish_vector_store.embed_tags(query.tags)
            context_dishes = dish_vector_store.search(query_vector, top_k=top_k)

        context_text = dish_vector_store.format_context(context_dishes) if context_dishes else ""

        system_prompt = (
            "Ты помощник по меню ресторана. "
            "Используй переданный список блюд как контекст. "
            "Если контекст пустой, отвечай общими фразами без конкретных блюд."
        )

        if context_text:
            system_prompt += f"\nКонтекст блюд:\n{context_text}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query.user_message},
        ]
        response = GIGA_CLIENT.send_message(messages)
        raw_payload = response["choices"][0]["message"]["content"]
        parsed_payload = json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload

        validated_response = RawRecommendationResponse.model_validate(parsed_payload)
        normalized_items = _normalize_recommendation_items(validated_response.items)
        return RecommendationResponse(items=normalized_items)
    except (json.JSONDecodeError, ValidationError):
        logger.exception("Failed to parse recommendations from GigaChat. Raw response: %s", raw_payload)
        raise HTTPException(
            status_code=502,
            detail="Не удалось обработать ответ рекомендательного сервиса"
        ) from None
    except Exception as e:
        logger.exception("Unexpected GigaChat error")
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

@app.on_event("startup")
async def startup_events():
    refresh_interval = int(os.getenv("EMBEDDINGS_REFRESH_SECONDS", "3600"))
    await dish_vector_store.rebuild_async()
    asyncio.create_task(periodic_embeddings_refresh(refresh_interval))

if __name__ == "__main__":
    app_host = os.getenv("APP_HOST", "127.0.0.1")
    app_port = int(os.getenv("APP_PORT", "8000"))
    uvicorn.run("main:app", host=app_host, port=app_port, reload=True)
