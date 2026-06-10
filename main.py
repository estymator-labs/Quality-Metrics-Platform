from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers.metrics import router as metrics_router

app = FastAPI(
    title="Sandmark - Quality Metrics",
    description="Analytical module for Sandmark AI code review metrics",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(metrics_router)


@app.get("/")
def root():
    return {
        "service": "QualityMetrics",
        "status": "running",
        "docs": "/docs",
        "summary": "/metrics/summary",
        "metrics": [
            "review_density",
            "defect_escape",
            "traceability",
            "risk_closure",
            "soup_completeness",
        ],
    }
