import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, validator
import jwt

pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str
    birth_date: str  # Формат: "YYYY-MM-DD"

    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3 or len(v) > 18:
            raise ValueError('Имя пользователя должно быть от 3 до 18 символов')
        return v

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 3 or len(v) > 18:
            raise ValueError('Пароль должен быть от 3 до 18 символов')
        if len(v.encode('utf-8')) > 72:
            raise ValueError('Пароль слишком длинный (более 72 байт)')
        return v


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(UserBase):
    id: str
    birth_date: str
    created_at: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    username: str

users_db = {}

SECRET_KEY = "your-secret-key-for-jwt-tokens"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

class AuthService:
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def register_user(user_data: UserCreate) -> dict:
        if user_data.username in users_db:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким именем уже существует"
            )

        for user in users_db.values():
            if user['email'] == user_data.email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Пользователь с таким email уже существует"
                )

        user_id = str(uuid.uuid4())
        hashed_password = AuthService.get_password_hash(user_data.password)

        users_db[user_data.username] = {
            'id': user_id,
            'username': user_data.username,
            'email': user_data.email,
            'hashed_password': hashed_password,
            'birth_date': user_data.birth_date,
            'created_at': datetime.now().isoformat()
        }

        access_token = AuthService.create_access_token(
            data={"sub": user_data.username, "user_id": user_id}
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user_id,
            "username": user_data.username
        }

    @staticmethod
    def authenticate_user(username: str, password: str) -> Optional[dict]:
        if username not in users_db:
            return None

        user = users_db[username]
        if not AuthService.verify_password(password, user['hashed_password']):
            return None

        return user

    @staticmethod
    def login_user(login_data: UserLogin) -> dict:
        user = AuthService.authenticate_user(login_data.username, login_data.password)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверное имя пользователя или пароль",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = AuthService.create_access_token(
            data={"sub": user['username'], "user_id": user['id']}
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user['id'],
            "username": user['username']
        }

    @staticmethod
    def get_current_user(token: str):
        try:
            if isinstance(token, bytes):
                token = token.decode('utf-8')

            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            user_id: str = payload.get("user_id")

            if username is None or user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Невалидный токен"
                )

            if username not in users_db:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Пользователь не найден"
                )

            user = users_db[username]
            if user['id'] != user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Невалидный токен"
                )

            return user

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Токен истёк"
            )
        except jwt.InvalidTokenError:  # ← ИСПРАВЛЕНО!
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Невалидный токен"
            )

    @staticmethod
    def get_user_profile(username: str) -> dict:
        if username not in users_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )

        user = users_db[username]
        return {
            "id": user['id'],
            "username": user['username'],
            "email": user['email'],
            "birth_date": user['birth_date'],
            "created_at": user['created_at']
        }

    @staticmethod
    def get_all_users() -> list:
        return list(users_db.values())


auth_service = AuthService()