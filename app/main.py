from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from app.schemas import ProductInput, ProductCard
from app.services.generator import ProductGenerator
from app.services.client import LLMServiceError
from app.services.validator import GenerationValidationError

from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import logging


app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static",
)

logger = logging.getLogger(__name__)
@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok"}

@app.post("/api/products/validate")
async def validate_product(product: ProductInput):
    return JSONResponse(
        content={
            "status": "valid",
            "product": product.model_dump(),
        }
    )

@app.post("/api/products/generate",response_model=ProductCard)
async def generate_product(product: ProductInput):
    try:
        generator = ProductGenerator()
        return await generator.generate(product)

    except LLMServiceError as exc:
        logger.error("LLM service error: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    except GenerationValidationError as exc:
        logger.error("Generation validation error: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc