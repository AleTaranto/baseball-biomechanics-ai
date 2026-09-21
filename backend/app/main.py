from fastapi import FastAPI

from app.api.routes.analysis import router as analysis_router
from app.api.routes.benchmark import router as benchmark_router
from app.api.routes.health import router as health_router
from app.api.routes.pipeline import router as pipeline_router
from app.api.routes.videos import router as videos_router
from app.core.config import get_settings
from app.core.logging import configure_logging

configure_logging()
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
    description="Early-stage platform for baseball swing analysis and biomechanical insight.",
)

app.include_router(health_router)
app.include_router(videos_router)
app.include_router(analysis_router)
app.include_router(pipeline_router)
app.include_router(benchmark_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": f"{settings.app_name} is running"}
