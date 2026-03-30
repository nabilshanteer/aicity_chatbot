from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.database import engine
from app import models
from app.api import auth, notes, chat, cases

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Citizens Advice Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(auth.router)
app.include_router(notes.router)
app.include_router(chat.router)
app.include_router(cases.router)


@app.get("/health")
def health():
    return {"status": "ok"}

