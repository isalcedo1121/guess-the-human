"""FastAPI entry point for Guess the Human."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import PROJECT_ROOT, Settings

FRONTEND_DIR = PROJECT_ROOT / "frontend"


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
    application.mount(
        "/static", StaticFiles(directory=FRONTEND_DIR / "static"), name="static"
    )

    @application.get("/", include_in_schema=False)
    def host_page() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "host.html")

    @application.get("/participant-preview", include_in_schema=False)
    def participant_preview() -> FileResponse:
        """Serve the form layout without creating or claiming a real room."""
        return FileResponse(FRONTEND_DIR / "participant.html")

    @application.get("/health", tags=["status"])
    def health() -> dict[str, str]:
        """Check the web process only; external services are not connected yet."""
        return {"status": "ok"}

    return application


app = create_app()
