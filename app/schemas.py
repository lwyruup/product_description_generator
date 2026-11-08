from pydantic import BaseModel, Field, ConfigDict, field_validator


class ProductInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1)
    manufacturer: str | None = None
    specs: dict[str, str] = Field(default_factory=dict)
    description: str | None = None

    @field_validator("specs")
    @classmethod
    def validate_specs(cls, value: dict[str, str]) -> dict[str, str]:
        return {
            key.strip(): val.strip()
            for key, val in value.items()
            if key.strip()
        }


class ProductCard(BaseModel):
    seo_title: str = Field(max_length=70)

    seo_description: str = Field(
        min_length=800,
        max_length=1200,
    )

    specifications: dict[str, str]

    search_queries: list[str] = Field(
        min_length=3,
        max_length=5,
    )

    commercial_block: str
    missing_fields: list[str] = Field(default_factory=list)