"""FastAPI entry point for Guess the Human."""

import json
import logging
from contextlib import asynccontextmanager
from html import escape

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from google.api_core.exceptions import GoogleAPICallError, RetryError
from google.auth.exceptions import GoogleAuthError

from backend.config import PROJECT_ROOT, Settings
from backend.rooms import router
from backend.storage import RoomError, connect_store

FRONTEND_DIR = PROJECT_ROOT / "frontend"


def create_app(settings: Settings | None = None, room_store=None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        logging.basicConfig(level=settings.log_level)
        logging.getLogger(__name__).info(
            "Starting Guess the Human (%s)", settings.app_env
        )
        owned_store = None
        if application.state.room_store is None:
            try:
                owned_store = connect_store(settings)
                application.state.room_store = owned_store
            except (ValueError, OSError):
                logging.getLogger(__name__).error("Firestore credentials could not be loaded.")
        try:
            yield
        finally:
            if owned_store is not None:
                owned_store.client.close()

    application = FastAPI(
        title="Guess the Human",
        description="A host-led Human or AI guessing game.",
        lifespan=lifespan,
    )
    application.state.settings = settings
    application.state.room_store = room_store
    application.include_router(router)

    @application.exception_handler(RoomError)
    async def room_error(request, exc):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    async def storage_error(request, exc):
        logging.getLogger(__name__).warning("Firestore request failed: %s", type(exc).__name__)
        return JSONResponse(status_code=503, content={
            "detail": "Room storage is unavailable. Please try again.",
        })

    for error in (GoogleAPICallError, RetryError, GoogleAuthError):
        application.add_exception_handler(error, storage_error)
    application.mount(
        "/static", StaticFiles(directory=FRONTEND_DIR / "static"), name="static"
    )

    @application.middleware("http")
    async def prevent_stale_pages(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    def host_document() -> HTMLResponse:
        questions = json.loads((FRONTEND_DIR / "static/questions.json").read_text())
        options = "\n".join(
            f'<option value="{escape(q, quote=True)}">{escape(q)}</option>'
            for q in questions
        )
        html = (FRONTEND_DIR / "host.html").read_text().replace(
            '<!-- preset-questions -->', options
        )
        return HTMLResponse(html)

    @application.get("/", include_in_schema=False)
    def host_page() -> HTMLResponse:
        return host_document()

    @application.get("/host/{room_id}", include_in_schema=False)
    def host_room_page(room_id: str) -> HTMLResponse:
        return host_document()

    @application.get("/room/{room_id}", include_in_schema=False)
    def participant_page(room_id: str) -> FileResponse:
        return FileResponse(FRONTEND_DIR / "participant.html")

    @application.get("/health", tags=["status"])
    def health() -> dict[str, str]:
        """Check the web process only; this does not probe external services."""
        return {"status": "ok"}

    return application


app = create_app()
