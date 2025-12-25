"""Утилиты для взаимодействия с GigaChat и рекомендациями.

Зависимости:
- requests
- urllib3
"""

import json
import logging
import os
import re
import uuid
from typing import Any, Dict, List, Sequence

import requests
import urllib3
from fastapi import HTTPException
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class RecommendationRequest(BaseModel):
    tags: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    restrictions: List[str] = Field(default_factory=list)


class GigaChatQuery(BaseModel):
    user_message: str
    tags: List[str] = Field(default_factory=list)
    top_k: int = 5


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


class GigaChatClient:
    def __init__(self, credentials: str):
        if not credentials:
            raise RuntimeError("GIGACHAT_CREDENTIALS is not configured")
        self.credentials = credentials
        self.access_token: str | None = None
        self._get_token()

    def _get_token(self) -> None:
        url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        payload = {"scope": "GIGACHAT_API_PERS"}
        headers = {
            "Authorization": f"Basic {self.credentials}",
            "RqUID": str(uuid.uuid4()),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        response = requests.post(url, data=payload, headers=headers, verify=False)
        response.raise_for_status()
        self.access_token = response.json()["access_token"]

    def send_message(self, messages: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.access_token:
            self._get_token()

        url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = {"model": "GigaChat", "messages": list(messages)}
        response = requests.post(url, json=payload, headers=headers, verify=False)
        if response.status_code == 401:
            self._get_token()
            headers["Authorization"] = f"Bearer {self.access_token}"
            response = requests.post(url, json=payload, headers=headers, verify=False)

        response.raise_for_status()
        return response.json()


def create_gigachat_client_from_env(env_var: str = "GIGACHAT_CREDENTIALS") -> GigaChatClient:
    credentials = os.getenv(env_var)
    return GigaChatClient(credentials=credentials)


def normalize_recommendation_items(items: List[RawRecommendationItem]) -> List[RecommendationItem]:
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


def request_recommendations(client: GigaChatClient, messages: Sequence[Dict[str, Any]]) -> RecommendationResponse:
    raw_payload: Any | None = None
    try:
        response = client.send_message(messages)
        raw_payload = response["choices"][0]["message"]["content"]
        parsed_payload = json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload

        validated_response = RawRecommendationResponse.model_validate(parsed_payload)
        normalized_items = normalize_recommendation_items(validated_response.items)
        return RecommendationResponse(items=normalized_items)
    except (json.JSONDecodeError, ValidationError):
        logger.exception("Failed to parse recommendations from GigaChat. Raw response: %s", raw_payload)
        raise HTTPException(
            status_code=502,
            detail="Не удалось обработать ответ рекомендательного сервиса",
        ) from None


def build_recommendation_prompt(
    context_dishes: List[Dict[str, Any]], request: RecommendationRequest
) -> Dict[str, str]:
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
        "user": "\n".join(user_parts),
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


def build_contextual_messages(query: GigaChatQuery, dish_vector_store: Any) -> List[Dict[str, str]]:
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

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query.user_message},
    ]


__all__ = [
    "GigaChatClient",
    "GigaChatQuery",
    "RecommendationItem",
    "RecommendationRequest",
    "RecommendationResponse",
    "RawRecommendationItem",
    "RawRecommendationResponse",
    "build_contextual_messages",
    "build_recommendation_prompt",
    "create_gigachat_client_from_env",
    "normalize_recommendation_items",
    "parse_recommendation_response",
    "request_recommendations",
]
