import json
import logging
import re

from groq import (
    AsyncGroq,
    APIError,
    APITimeoutError,
    RateLimitError,
)
from app.config import settings
from app.prompts.product import (
    SYSTEM_PROMPT,
    FACT_CONTROL_RULES,
    FACT_REVIEW_PROMPT
)
from app.schemas import ProductInput


logger = logging.getLogger(__name__)


class LLMServiceError(Exception):
    pass


class LLMService:
    def __init__(self):
        if not settings.groq_api_key:
            raise LLMServiceError("GROQ_API_KEY не указан в конфигурации")

        self.client = AsyncGroq(api_key=settings.groq_api_key,timeout=30.0,max_retries=2)

    @staticmethod
    def parse_json_response(content: str) -> dict:
        content = content.strip()
        content = re.sub(r"^```(?:json)?\s*","",content,flags=re.IGNORECASE)
        content = re.sub(r"\s*```$","",content)

        try:
            result = json.loads(content)

        except json.JSONDecodeError as exc:
            raise LLMServiceError("Модель вернула некорректный JSON") from exc

        if not isinstance(result, dict):
            raise LLMServiceError("Ответ модели должен быть JSON-объектом")
        return result

    async def _request(
        self,
        messages: list[dict],
        max_tokens: int = 3500,
        temperature: float = 0.1,
    ) -> str:

        try:
            response = await self.client.chat.completions.create(
                model=settings.groq_model,
                messages=messages,
                temperature=temperature,
                max_completion_tokens=max_tokens,
                reasoning_effort="low",
            )

            content = response.choices[0].message.content

            if not content:
                raise LLMServiceError("Модель вернула пустой ответ")
            return content.strip()

        except RateLimitError as exc:
            raise LLMServiceError("Превышен лимит запросов Groq API") from exc

        except APITimeoutError as exc:
            raise LLMServiceError("Превышено время ожидания Groq API") from exc

        except APIError as exc:
            logger.exception("Groq API error")

            raise LLMServiceError("Ошибка при обращении к Groq API") from exc

        except (IndexError, AttributeError) as exc:
            raise LLMServiceError("Модель вернула некорректный ответ") from exc

    async def generate(self,product: ProductInput,feedback: list[str] | None = None) -> dict:
        payload = product.model_dump_json(ensure_ascii=False)
        user_content = payload

        if feedback:
            user_content += (
                "\n\nПРЕДЫДУЩАЯ ГЕНЕРАЦИЯ "
                "НЕ ПРОШЛА ПРОВЕРКУ:\n"
                + "\n".join(
                    f"- {error}"
                    for error in feedback
                )
                + "\n\n"
                "Создай карточку заново с учётом ошибок. "
                "Не добавляй неподтверждённые характеристики."
            )

        content = await self._request(
            messages=[
                {
                    "role": "system",
                    "content": (
                        SYSTEM_PROMPT
                        + "\n\n"
                        + FACT_CONTROL_RULES
                    ),
                },
                {
                    "role": "user",
                    "content": user_content,
                },
            ],
            temperature=0.2,
            max_tokens=3500,
        )

        return self.parse_json_response(content)

    async def review_card(self,product: ProductInput,generated: dict) -> dict:
        source_json = product.model_dump_json(
            ensure_ascii=False,
            indent=2,
        )

        generated_json = json.dumps(generated, ensure_ascii=False, indent=2)

        user_content = (
            "ИСХОДНЫЕ ДАННЫЕ:\n"
            + source_json
            + "\n\n"
            + "СГЕНЕРИРОВАННАЯ КАРТОЧКА:\n"
            + generated_json
            + "\n\n"
            + "Проверь карточку и исправь "
              "неподтверждённые утверждения."
        )

        content = await self._request(
            messages=[
                {
                    "role": "system",
                    "content": FACT_REVIEW_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_content,
                },
            ],
            temperature=0.0,
            max_tokens=3500,
        )

        return self.parse_json_response(content)