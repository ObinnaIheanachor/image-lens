from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routes import router
from src.db.session import init_db
from src.services.processor import processor


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    processor.start()
    try:
        yield
    finally:
        processor.stop()


app = FastAPI(title="Image Insight", lifespan=lifespan)
app.include_router(router)
