from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routes import queue_backend, router
from src.db.session import init_db


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
app.include_router(router)
