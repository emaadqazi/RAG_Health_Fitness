from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_chat import router as chat_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(title="Health/Fitness RAG Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
