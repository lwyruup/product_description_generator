from pydantic import ValidationError
from app.schemas import ProductInput, ProductCard
import re

class GenerationValidationError(Exception):
    pass


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def build_seo_title(product: ProductInput,selected_spec_keys: list[str] | None = None) -> str:
    max_length = 70

    name = " ".join(product.name.split())
    manufacturer = " ".join((product.manufacturer or "").split())

    if len(name) > max_length:
        raise GenerationValidationError("Название товара превышает 70 символов")

    title = name

    if manufacturer and normalize_text(manufacturer) not in normalize_text(name):
        candidate = f"{title} — {manufacturer}"
        if len(candidate) <= max_length:
            title = candidate

    if not isinstance(selected_spec_keys, list):
        selected_spec_keys = []

    added_values = set()

    for key in selected_spec_keys:
        if not isinstance(key, str):
            continue

        value = product.specs.get(key)

        if not isinstance(value, str) or not value.strip():
            continue

        normalized_value = normalize_text(value)

        if normalized_value in added_values:
            continue

        if normalized_value in normalize_text(title):
            continue

        title_words = set(normalize_text(name).split())
        value_words = set(normalized_value.split())

        if value_words and value_words.issubset(title_words):
            continue

        candidate = f"{title}, {value.strip()}"

        if len(candidate) > max_length:
            continue

        title = candidate
        added_values.add(normalized_value)

        if len(added_values) >= 2:
            break

    return title

def normalize_missing_fields(product: ProductInput, missing_fields: list) -> list[str]:
    if not isinstance(missing_fields, list):
        return []

    existing_keys = {
        normalize_text(key)
        for key in product.specs
    }

    result = []
    seen = set()

    for field in missing_fields:
        if not isinstance(field, str):
            continue

        field = " ".join(field.split())
        normalized = normalize_text(field)

        if not normalized:
            continue

        if normalized in existing_keys:
            continue

        if normalized in seen:
            continue

        result.append(field)
        seen.add(normalized)

        if len(result) >= 5:
            break

    return result

def validate_generated_card(product: ProductInput, generated: dict) -> ProductCard:
    if not isinstance(generated, dict):
        raise GenerationValidationError("Ответ модели должен быть JSON-объектом")

    specifications = {
        key: value if value else "данных нет"
        for key, value in product.specs.items()
    }

    card_data = {
        "seo_title": build_seo_title(product,generated.get("seo_spec_keys", [])),

        "seo_description": generated.get(
            "seo_description",
            "",
        ),

        "specifications": specifications,

        "search_queries": generated.get(
            "search_queries",
            [],
        ),

        "commercial_block": generated.get(
            "commercial_block",
            "",
        ),

        "missing_fields": normalize_missing_fields(product,generated.get("missing_fields", [])),
    }

    try:
        return ProductCard.model_validate(card_data)

    except ValidationError as exc:
        raise GenerationValidationError(f"Результат не соответствует схеме: {exc}") from exc