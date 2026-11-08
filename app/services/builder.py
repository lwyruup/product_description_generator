import re
from app.schemas import ProductInput


MIN_DESCRIPTION_LENGTH = 800
MAX_DESCRIPTION_LENGTH = 1200


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip()


def build_verified_facts(product: ProductInput) -> str:
    lines = [
        f"Название товара: {normalize_text(product.name)}"
    ]

    if product.manufacturer:
        lines.append(f"Производитель: {normalize_text(product.manufacturer)}")

    if product.description:
        lines.append("Исходное описание: "+ normalize_text(product.description))

    if product.specs:
        lines.append("Технические характеристики:")
        for key, value in product.specs.items():
            if value and str(value).strip():
                lines.append(
                    f"- {normalize_text(key)}: {normalize_text(value)}"
                )

    return "\n".join(lines)


def extract_technical_values(text: str) -> set[str]:
    pattern = (
        r"(?<!\w)"
        r"\d+(?:[.,]\d+)?"
        r"\s*"
        r"(?:МПа|кПа|Па|бар|bar|мм|см|м|"
        r"°C|°С|В|V|А|мА|Ом|Ω|Гц|Hz|"
        r"кг|г|Вт|W)"
        r"(?!\w)"
    )

    matches = re.findall(pattern,text,flags=re.IGNORECASE)

    return {
        normalize_text(value).casefold().replace(" ", "")
        for value in matches
    }


def find_unsupported_values(product: ProductInput,generated_text: str) -> list[str]:
    source_text = build_verified_facts(product)

    allowed_values = extract_technical_values(source_text)
    generated_values = extract_technical_values(generated_text)

    return sorted(generated_values - allowed_values)


def validate_description(product: ProductInput, description: str) -> list[str]:
    errors = []
    if not isinstance(description, str):
        return ["SEO-описание должно быть строкой."]

    length = len(description)

    if length < MIN_DESCRIPTION_LENGTH:
        errors.append(f"SEO-описание слишком короткое: "f"{length} символов вместо минимум 800.")

    if length > MAX_DESCRIPTION_LENGTH:
        errors.append(f"SEO-описание слишком длинное: "f"{length} символов вместо максимум 1200.")

    return errors