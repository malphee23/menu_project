#python main.py - для запуска локального сайта в терминале PyCharm или cmd
#http://127.0.0.1:8000/docs - интерактивная документация
#Ip и порт будет показан в терминале или cmd
import uuid
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(
    title="Restaurant API",
    description="API for restaurant service",
)

class VisitPurpose(BaseModel):
    purpose: str

class TastePreferences(BaseModel):
    preferences: List[str]

class DietaryRestrictions(BaseModel):
    restrictions: List[str]
    allergies: List[str]

class VisitorData(BaseModel):
    table_number: int  # Номер столика
    visit_purpose: VisitPurpose
    taste_preferences: Optional[TastePreferences] = None
    dietary_restrictions: Optional[DietaryRestrictions] = None
    people_count: int

visitor_submissions = []

@app.post("/submit-visit-info", tags=["Клиент"], summary="Информации заявки")
async def submit_visit_info(data: VisitorData):
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

    return{
        "success": True,
        "message": "Ваш заказ принят, ожидайте",
        "table_number": data.table_number,
    }

@app.get("/submissions", tags=["Персонал"], summary="Получить все заявки")
async def get_all_submissions():
    return{
        "submissions": visitor_submissions,
        "total": len(visitor_submissions),
    }

@app.get("/submissions/{table_number}", tags=["Персонал"], summary="Заявки определенного стола")
async def get_table_submission(table_number: int):
    table_subs = [s for s in visitor_submissions if s["table_number"] == table_number]
    return{
        "submissions": table_subs,
    }

@app.put("/complete/{table_number}", tags=["Персонал"], summary="Обнулить заказы определенного стола")
async def mark_table_completed(table_number: int):
    # Удаляем заявки этого столика
    global visitor_submissions
    visitor_submissions = [
        s for s in visitor_submissions
        if s["table_number"] != table_number
    ]
    return {"message": f"Столик {table_number} обслужен"}

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)