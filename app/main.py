from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import (
    ApiValidationError,
    api_validation_error_handler,
    request_validation_error_handler,
)
from app.api.routers import (
    annotations,
    auth,
    documents,
    exports,
    imports,
    labels,
)
from app.core.cache import close_redis
from app.core.config import get_settings
from app.db.session import close_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await close_redis()
    await close_db()


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.add_exception_handler(ApiValidationError, api_validation_error_handler)
app.add_exception_handler(
    RequestValidationError,
    request_validation_error_handler,
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(imports.router)
app.include_router(exports.router)
app.include_router(labels.router)
app.include_router(annotations.router)


@app.get('/health')
async def health() -> dict[str, str]:
    return {'status': 'ok'}
