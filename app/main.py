"""FastAPI entry point for the London Loneliness Risk Dashboard."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.api.routes import router as api_router
from app.data.loader import load_and_prepare


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load and cache data on startup
    load_and_prepare()
    yield


app = FastAPI(
    title="London Loneliness Risk Dashboard",
    lifespan=lifespan,
)

app.include_router(api_router)

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
def index():
    return FileResponse(str(static_dir / "index.html"))
