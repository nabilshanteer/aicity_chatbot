from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.database import engine
from app import models
from app.api import auth

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Citizens Advice Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(auth.router, prefix="/api/auth")


@app.get("/health")
def health():
    return {"status": "ok"}

