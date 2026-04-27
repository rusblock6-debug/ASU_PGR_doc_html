import os
import logging
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import chromadb
from chromadb.config import Settings
import redis
import hashlib
import json
from datetime import datetime

# Настройка логирования
os.makedirs("logs", exist_ok=True)
handler = RotatingFileHandler('logs/ai-bot.log', maxBytes=10_000_000, backupCount=5)
logging.basicConfig(
    handlers=[handler],
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="АСУ ПГР RAG Assistant")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация клиентов
chroma_client = chromadb.Client(Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory="/app/chroma_data"
))

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)

API_KEY = os.getenv("API_KEY")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")

# Модели
class QuestionRequest(BaseModel):
    question: str
    
class AnswerResponse(BaseModel):
    answer: str
    sources: List[dict]
    cached: bool = False
    response_time: float

# Вспомогательные функции
def verify_api_key(x_api_key: Optional[str] = Header(None)):
    if not API_KEY:
        raise HTTPException(500, "API_KEY не настроен")
    if x_api_key != API_KEY:
        raise HTTPException(401, "Неверный API-ключ")

@app.get("/health")
async def health():
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "ollama": "connected",
        "chroma": "connected",
        "redis": redis_client.ping()
    }

@app.post("/api/ask")
async def ask_question(req: QuestionRequest):
    """Ответ на вопрос пользователя"""
    start_time = datetime.now()
    logger.info(f"Получен вопрос: {req.question}")
    
    # Проверка кэша
    cache_key = f"q:{hashlib.md5(req.question.encode()).hexdigest()}"
    cached = redis_client.get(cache_key)
    
    if cached:
        logger.info("Ответ из кэша")
        response = json.loads(cached)
        response["cached"] = True
        response["response_time"] = (datetime.now() - start_time).total_seconds()
        return response
    
    # TODO: Реализация RAG-поиска
    # 1. Embedding вопроса
    # 2. Поиск в ChromaDB (top-20)
    # 3. Reranking (top-4)
    # 4. Генерация ответа через Ollama
    
    answer = {
        "answer": "Бот в процессе индексации. Пожалуйста, подождите завершения индексации.",
        "sources": [],
        "cached": False,
        "response_time": (datetime.now() - start_time).total_seconds()
    }
    
    # Кэширование
    redis_client.setex(cache_key, 3600, json.dumps(answer))
    
    logger.info(f"Ответ сгенерирован за {answer['response_time']:.2f}с")
    return answer

@app.post("/api/snapshot/create")
async def create_snapshot(x_api_key: Optional[str] = Header(None)):
    """Создание снимка репозитория"""
    verify_api_key(x_api_key)
    
    logger.info("Создание снимка репозитория...")
    
    # TODO: Реализация сканирования файлов
    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "files": [],
        "excluded": [".git", "node_modules", "__pycache__", "logs"]
    }
    
    # Сохранение снимка
    snapshot_path = f"/app/snapshots/snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Снимок создан: {snapshot_path}")
    return {"status": "created", "path": snapshot_path}

@app.get("/api/snapshot/latest")
async def get_latest_snapshot():
    """Получение последнего снимка"""
    # TODO: Реализация чтения последнего снимка
    return {"status": "not_implemented"}

@app.post("/api/index")
async def index_repository(
    mode: str = "full",
    snapshot: Optional[str] = None,
    x_api_key: Optional[str] = Header(None)
):
    """Индексация репозитория"""
    verify_api_key(x_api_key)
    
    logger.info(f"Запуск индексации: mode={mode}, snapshot={snapshot}")
    
    # TODO: Реализация индексации
    # 1. Сканирование файлов (с учётом чёрного списка)
    # 2. Чанкование (Tree-sitter для кода)
    # 3. Embedding
    # 4. Сохранение в ChromaDB
    
    return {"status": "indexing_started", "mode": mode}

@app.post("/api/reindex")
async def reindex_repository(
    mode: str = "incremental",
    x_api_key: Optional[str] = Header(None)
):
    """Переиндексация (инкрементальная или полная)"""
    verify_api_key(x_api_key)
    
    logger.info(f"Запуск переиндексации: mode={mode}")
    
    # TODO: Реализация инкрементальной индексации
    # 1. Вычисление MD5-хешей файлов
    # 2. Сравнение с хешами в ChromaDB
    # 3. Обновление только изменённых файлов
    
    return {"status": "reindexing_started", "mode": mode}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
