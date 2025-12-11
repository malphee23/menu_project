import os
import uuid
from datetime import datetime
from typing import Optional, Dict

from fastapi import HTTPException, status, APIRouter
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, field_validator
from dotenv import load_dotenv, find_dotenv
from sqlalchemy import text

from database import db

# Загружаем переменные окружения (.env / env / env.example)
dotenv_path = (
    find_dotenv(usecwd=True)
    or find_dotenv("env", usecwd=True)
    or find_dotenv("env.example", usecwd=True)
)
if dotenv_path:
    load_dotenv(dotenv_path)

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")

pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

auth_router = APIRouter(prefix="/auth", tags=["Аутентификация"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Пароль должен быть не менее 6 символов")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    success: bool
    user_id: str
    email: EmailStr
    token: str


def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def _issue_token(user_id: str, email: str) -> str:
    return pwd_context.hash(f"{user_id}:{email}:{SECRET_KEY}")[:32]


def _ensure_users_table():
    if db._table_exists("users"):
        return
    with db.engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    login TEXT UNIQUE,
                    password_hash TEXT,
                    birth_date DATE,
                    diet_type TEXT,
                    meal_style TEXT
                )
                """
            )
        )


def _get_user_by_email(email: str) -> Optional[Dict[str, str]]:
    _ensure_users_table()
    with db.engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, login, password_hash FROM users WHERE login = :email"),
            {"email": email},
        ).fetchone()
        return dict(row._mapping) if row else None


def _create_user(email: str, password_hash: str) -> Dict[str, str]:
    _ensure_users_table()
    with db.engine.begin() as conn:
        result = conn.execute(
            text(
                """
                INSERT INTO users (login, password_hash)
                VALUES (:email, :password_hash)
                """
            ),
            {"email": email, "password_hash": password_hash},
        )
        user_id = result.lastrowid
    return {"id": user_id, "login": email, "password_hash": password_hash}


@auth_router.post("/register", response_model=AuthResponse, summary="Регистрация")
def register_user(payload: RegisterRequest):
    email = payload.email.lower()

    existing = _get_user_by_email(email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует",
        )

    password_hash = _hash_password(payload.password)
    user_row = _create_user(email, password_hash)
    user_id = str(user_row["id"])

    token = _issue_token(user_id, email)
    return AuthResponse(success=True, user_id=user_id, email=email, token=token)


@auth_router.post("/login", response_model=AuthResponse, summary="Вход")
def login_user(payload: LoginRequest):
    email = payload.email.lower()
    user = _get_user_by_email(email)
    if not user or not _verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    user_id = str(user["id"])
    token = _issue_token(user_id, email)
    return AuthResponse(success=True, user_id=user_id, email=email, token=token)