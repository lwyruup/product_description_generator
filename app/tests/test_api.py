from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.client import LLMServiceError
from app.services.validator import GenerationValidationError


client = TestClient(app)


PRODUCT = {
    "name": "Манометр DM 02",
    "manufacturer": "Манотомь",
    "specs": {
        "диапазон измерений": "0–1,6 МПа",
        "класс точности": "1,5"
    },
    "description": "Манометр для измерения давления."
}


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_index():
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_validate_product():
    response = client.post(
        "/api/products/validate",
        json=PRODUCT,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "valid"


def test_validate_product_without_name():
    invalid_product = {
        "manufacturer": "Манотомь",
        "specs": {}
    }

    response = client.post(
        "/api/products/validate",
        json=invalid_product,
    )

    assert response.status_code == 422


def test_generate_success():
    generated_card = {
        "seo_title": "Манометр DM 02",
        "seo_description": "Описание манометра. " * 50,
        "specifications": PRODUCT["specs"],
        "search_queries": [
            "Манометр DM 02",
            "Манометр Манотомь",
            "Манометр 0–1,6 МПа"
        ],
        "commercial_block": "Манометр для измерения давления.",
        "missing_fields": []
    }

    with patch("app.main.ProductGenerator") as generator_class:
        generator = generator_class.return_value
        generator.generate = AsyncMock(
            return_value=generated_card
        )

        response = client.post(
            "/api/products/generate",
            json=PRODUCT,
        )

    assert response.status_code == 200
    assert response.json()["seo_title"] == "Манометр DM 02"


def test_generate_llm_error():
    with patch("app.main.ProductGenerator") as generator_class:
        generator = generator_class.return_value
        generator.generate = AsyncMock(
            side_effect=LLMServiceError("Ошибка Groq API")
        )

        response = client.post(
            "/api/products/generate",
            json=PRODUCT,
        )

    assert response.status_code == 502


def test_generate_validation_error():
    with patch("app.main.ProductGenerator") as generator_class:
        generator = generator_class.return_value
        generator.generate = AsyncMock(
            side_effect=GenerationValidationError(
                "Ошибка проверки карточки"
            )
        )

        response = client.post(
            "/api/products/generate",
            json=PRODUCT,
        )

    assert response.status_code == 422