from fastapi import FastAPI

from collab_engine.api.ws import router as ws_router
from collab_engine.logging_config import configure_logging


configure_logging()

app = FastAPI(title="collab-engine")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


app.include_router(ws_router)
