#python main.py - для запуска локального сайта в терминале PyCharm или cmd
#http://127.0.0.1:8000/docs - интерактивная документация
#Ip и порт будет показан в терминале или cmd

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="Restaurant API",
    description="API for restaurant service",
)

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)