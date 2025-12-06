#python main.py - для запуска локального сайта в терминале PyCharm или cmd
#http://127.0.0.1:8000/docs - интерактивная документация
#Ip и порт будет показан в терминале или cmd

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

app = FastAPI()

engine = create_async_engine('sqlite+aiosqlite:///users.db')

new_session = async_sessionmaker(engine, expire_on_commit=False)

async def get_session():
    async with new_session() as session:
        yield session

class Base(DeclarativeBase):
    pass

class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str]
    password: Mapped[str]

@app.post("/setup_db")
async def setup_db():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    return {"success": True}

#Обязательно нужна
if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)