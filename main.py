#python main.py - для запуска локального сайта в терминале PyCharm или cmd
#http://127.0.0.1:8000/docs - интерактивная документация
#Ip и порт будет показан в терминале или cmd

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

app = FastAPI(
    title="Restaurant API",
    description="API for restaurant service",
)

class UserCredentials(BaseModel):
    username: str
    password: str

users_storage = []

@app.post("/user/create", tags=["UsersLog"], summary="Создать пользователя")
def create_user(user: UserCredentials):
    for existing_user in users_storage:
        if existing_user["username"] == user.username:
            raise HTTPException(
                status_code=400,
                detail="Пользователь с таким именем уже существует",
            )

    user_data = {
        "username": user.username,
        "password": user.password,
    }

    users_storage.append(user_data)

    return {
        "message": "Пользователь успешно зарегистрирован",
    }

@app.get("/user/read", tags=["UsersLog"], summary="Список пользователей")
def read_user():
    return {
        "username": users_storage[0]["username"],
        "password": users_storage[0]["password"],
    }

@app.post("/login", tags=["UsersLog"], summary="Войти")
def login_user(user: UserCredentials):
    for stored_user in users_storage:
        if (stored_user["username"] == user.username and
            stored_user["password"] == user.password):
            return {
                "message": "Авторизация успешна",
                "username": user.username,
            }

    raise HTTPException(
        status_code=401,
        detail="Попробуйте снова"
    )

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)