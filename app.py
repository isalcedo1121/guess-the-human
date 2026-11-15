"""FastAPI entry point for Guess the Human."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        logging.basicConfig(level=settings.log_level)
        logging.getLogger(__name__).info(
            "Starting Guess the Human (%s)", settings.app_env
        )
        yield

    application = FastAPI(
        title="Guess the Human",
        description="A host-led Human or AI guessing game.",
        lifespan=lifespan,
    )

    @application.get("/health", tags=["status"])
    def health() -> dict[str, str]:
        """Check the web process only; external services are not connected yet."""
        return {"status": "ok"}

    return application


app = create_app()
