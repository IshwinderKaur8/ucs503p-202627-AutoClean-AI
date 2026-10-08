from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_assistant import router as assistant_router
from app.api.routes_dataset import router as dataset_router
from app.api.routes_pipeline import router as pipeline_router

app = FastAPI(title="AutoClean AI", description="Automated data preprocessing, cleaning, and feature engineering.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dataset_router)
app.include_router(pipeline_router)
app.include_router(assistant_router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
