# python main.py - для запуска локального сайта в терминале PyCharm или cmd
# http://127.0.0.1:8000/docs - интерактивная документация
# Ip и порт будет показан в терминале или cmd
# . venv/Scripts/activate

import os
import uuid
from datetime import datetime
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv, find_dotenv

from mobile import mobile_router
from admin import admin_router
from sofia_modules import orders_router, payments_router, reviews_router, kitchen_router
from auth import auth_router

from storage import *

from starlette.middleware.cors import CORSMiddleware

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

# Сессии и заказы

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

if __name__ == "__main__":
    app_host = os.getenv("APP_HOST", "127.0.0.1")
    app_port = int(os.getenv("APP_PORT", "8000"))
    uvicorn.run("main:app", host=app_host, port=app_port, reload=True)