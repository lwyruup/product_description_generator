from unittest.mock import AsyncMock

import pytest

from app.schemas import ProductInput, ProductCard
from app.services.generator import ProductGenerator
from app.services.validator import GenerationValidationError


@pytest.fixture
def product():
    return ProductInput(
        name="Манометр DM 02",
        manufacturer="Манотомь",
        specs={
            "диапазон измерений": "0–1,6 МПа",
            "класс точности": "1,5",
        },
        description="Манометр для измерения избыточного давления.",
    )


@pytest.fixture
def valid_generated():
    return {
        "seo_title": "Манометр DM 02",
        "seo_description": "Манометр DM 02 предназначен для измерения давления. " * 18,
        "specifications": {
            "диапазон измерений": "0–1,6 МПа",
            "класс точности": "1,5",
        },
        "search_queries": [
            "Манометр DM 02",
            "Манометр Манотомь",
            "Манометр 0–1,6 МПа",
        ],
        "commercial_block": "Манометр для измерения давления.",
        "missing_fields": [],
    }


@pytest.fixture
def generator():
    instance = ProductGenerator.__new__(ProductGenerator)
    instance.llm = AsyncMock()
    return instance


@pytest.mark.asyncio
async def test_successful_generation(generator, product, valid_generated):
    generator.llm.generate.return_value = valid_generated

    result = await generator.generate(product)

    assert isinstance(result, ProductCard)
    assert result.seo_title == "Манометр DM 02 — Манотомь"
    assert 800 <= len(result.seo_description) <= 1200

    generator.llm.generate.assert_awaited_once_with(product)
    generator.llm.review_card.assert_not_awaited()


@pytest.mark.asyncio
async def test_retry_when_description_too_short(
    generator,
    product,
    valid_generated,
):
    invalid_generated = {
        **valid_generated,
        "seo_description": "Слишком короткое описание.",
    }

    generator.llm.generate.side_effect = [
        invalid_generated,
        valid_generated,
    ]

    result = await generator.generate(product)

    assert isinstance(result, ProductCard)
    assert 800 <= len(result.seo_description) <= 1200

    assert generator.llm.generate.await_count == 2
    generator.llm.review_card.assert_not_awaited()


@pytest.mark.asyncio
async def test_retry_when_description_too_long(
    generator,
    product,
    valid_generated,
):
    invalid_generated = {
        **valid_generated,
        "seo_description": "Манометр для измерения давления. " * 50,
    }

    generator.llm.generate.side_effect = [
        invalid_generated,
        valid_generated,
    ]

    result = await generator.generate(product)

    assert isinstance(result, ProductCard)
    assert generator.llm.generate.await_count == 2


@pytest.mark.asyncio
async def test_invalid_description_after_retry(
    generator,
    product,
    valid_generated,
):
    invalid_generated = {
        **valid_generated,
        "seo_description": "Короткое описание.",
    }

    generator.llm.generate.side_effect = [
        invalid_generated,
        invalid_generated,
    ]

    with pytest.raises(GenerationValidationError):
        await generator.generate(product)

    assert generator.llm.generate.await_count == 2
    generator.llm.review_card.assert_not_awaited()


@pytest.mark.asyncio
async def test_specifications_preserved(
    generator,
    product,
    valid_generated,
):
    generator.llm.generate.return_value = valid_generated
    result = await generator.generate(product)
    assert result.specifications == product.specs