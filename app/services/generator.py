import logging

from app.schemas import ProductInput, ProductCard
from app.services.client import LLMService
from app.services.builder import validate_description
from app.services.validator import (
    validate_generated_card,
    GenerationValidationError,
)

logger = logging.getLogger(__name__)


class ProductGenerator:

    def __init__(self):
        self.llm = LLMService()

    async def generate(
        self,
        product: ProductInput,
    ) -> ProductCard:

        # Первая генерация
        generated = await self.llm.generate(product)

        # Проверяем длину описания
        description = generated.get("seo_description", "")

        if not isinstance(description, str):
            description = ""

        errors = validate_description(
            product,
            description,
        )

        # Если длина неправильная — одна повторная попытка
        if errors:
            logger.warning(
                "Generation validation errors: %s",
                errors,
            )

            generated = await self.llm.generate(
                product,
                feedback=errors,
            )

            description = generated.get("seo_description", "")

            if not isinstance(description, str):
                description = ""

            errors = validate_description(
                product,
                description,
            )

        if errors:
            raise GenerationValidationError(
                "Не удалось сформировать корректное SEO-описание: "
                + "; ".join(errors)
            )

        return validate_generated_card(
            product=product,
            generated=generated,
        )