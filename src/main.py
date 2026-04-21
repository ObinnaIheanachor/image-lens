import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import queue_backend, router
from src.config import settings
from src.db.session import init_db
from src.observability.logging import configure_logging, log_http_access
from src.observability.metrics import track_http_metrics
from src.observability.tracing import attach_trace_id
from src.services.sweepers import sweeper_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    app.state.startup_errors = []
    app.state.sweeper_stop_event = asyncio.Event()
    app.state.sweeper_task = None
    try:
        init_db()
    except Exception as exc:
        app.state.startup_errors.append(f"db_init_failed: {exc}")
    try:
        queue_backend.start()
    except Exception as exc:
        app.state.startup_errors.append(f"queue_start_failed: {exc}")
    if settings.enable_sweepers:
        app.state.sweeper_task = asyncio.create_task(sweeper_loop(app.state.sweeper_stop_event))
    try:
        yield
    finally:
        if app.state.sweeper_task:
            app.state.sweeper_stop_event.set()
            await app.state.sweeper_task
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
app.middleware("http")(attach_trace_id)
app.middleware("http")(log_http_access)
app.include_router(router)
