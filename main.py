#python main.py - для запуска локального сайта в терминале PyCharm или cmd
#http://127.0.0.1:8000/docs - интерактивная документация
#Ip и порт будет показан в терминале или cmd

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, EmailStr

app = FastAPI()

users = []

class UserSchema(BaseModel):
    email: EmailStr
    login: str | None
    password: str = Field(..., min_length=3, max_length=16)

@app.post("/users")
def add_user(user: UserSchema):
    users.append(user)
    return {"ok": True, "msg": "user added"}

@app.get("/users")
def get_users():
    return users

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)