from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from backend.routers.metrics import router as metrics_router

app = FastAPI(title="Sandmark — Quality Metrics")
app.include_router(metrics_router)
