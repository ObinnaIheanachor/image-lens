from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import queue_backend, router
from src.config import settings
from src.db.session import init_db
from src.observability.metrics import track_http_metrics


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.startup_errors = []
    try:
        init_db()
    except Exception as exc:
        app.state.startup_errors.append(f"db_init_failed: {exc}")
    try:
        queue_backend.start()
    except Exception as exc:
        app.state.startup_errors.append(f"queue_start_failed: {exc}")
    try:
        yield
    finally:
        queue_backend.stop()


app = FastAPI(title="Image Insight", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(track_http_metrics)
app.include_router(router)
