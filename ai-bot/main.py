import os
import logging
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import chromadb
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
chroma_client = chromadb.PersistentClient(path="/app/chroma_data")

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)

API_KEY = os.getenv("API_KEY")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")

# Системный промпт для AI
SYSTEM_PROMPT = """Ты — технический ассистент для системы "АСУ ПГР" (Автоматизированная Система Управления Подземными Горными Работами).

ТВОЯ РОЛЬ:
- Отвечай на вопросы по документации, коду и архитектуре проекта "Цифровой двойник карьера"
- Используй ТОЛЬКО информацию из предоставленного контекста
- Давай точные, технические ответы для разработчиков

ПРАВИЛА ОТВЕТОВ:
1. Ответ должен быть 3-5 предложений (максимум 8)
2. Указывай конкретные файлы и компоненты
3. Если информации нет в контексте — честно скажи "Информация не найдена в документации"
4. НЕ отвечай на вопросы не связанные с проектом (философия, личные советы, общие темы)
5. Используй технический язык, но понятный

ОГРАНИЧЕНИЯ:
- Отвечай ТОЛЬКО на вопросы о: коде, архитектуре, микросервисах, API, базах данных, конфигурации, документации проекта
- НЕ отвечай на: личные вопросы, общие темы, философию, советы по жизни, цены, погоду

ФОРМАТ ОТВЕТА:
Краткий технический ответ с указанием источника (файл/компонент).

Контекст из документации:
{context}

Вопрос: {question}

Ответ:"""

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
    
    # Проверка на нерелевантные вопросы
    irrelevant_keywords = ['жизнь', 'любовь', 'счастье', 'золото', 'цена', 'погода', 'курс', 'политика']
    if any(keyword in req.question.lower() for keyword in irrelevant_keywords):
        return {
            "answer": "Я отвечаю только на технические вопросы по проекту АСУ ПГР. Пожалуйста, задайте вопрос о коде, архитектуре, микросервисах или документации проекта.",
            "sources": [],
            "cached": False,
            "response_time": (datetime.now() - start_time).total_seconds()
        }
    
    # Проверка кэша
    cache_key = f"q:{hashlib.md5(req.question.encode()).hexdigest()}"
    cached = redis_client.get(cache_key)
    
    if cached:
        logger.info("Ответ из кэша")
        response = json.loads(cached)
        response["cached"] = True
        response["response_time"] = (datetime.now() - start_time).total_seconds()
        return response
    
    try:
        # Получаем коллекцию
        collection = chroma_client.get_or_create_collection(name="pgr_docs")
        
        # Проверяем есть ли документы
        count = collection.count()
        if count == 0:
            return {
                "answer": "База знаний пуста. Необходимо запустить индексацию репозитория через API: POST /api/index?mode=full",
                "sources": [],
                "cached": False,
                "response_time": (datetime.now() - start_time).total_seconds()
            }
        
        # Поиск похожих документов
        results = collection.query(
            query_texts=[req.question],
            n_results=min(5, count)
        )
        
        if not results['documents'] or not results['documents'][0]:
            return {
                "answer": "По вашему вопросу не найдено релевантной информации в документации. Попробуйте переформулировать вопрос или задать более конкретный.",
                "sources": [],
                "cached": False,
                "response_time": (datetime.now() - start_time).total_seconds()
            }
        
        # Формируем контекст
        context_parts = []
        sources = []
        for i, doc in enumerate(results['documents'][0]):
            metadata = results['metadatas'][0][i] if results['metadatas'] else {}
            context_parts.append(f"[Источник {i+1}]: {doc}")
            sources.append({
                "file": metadata.get('file', 'unknown'),
                "line": metadata.get('line', None),
                "type": metadata.get('type', 'text')
            })
        
        context = "\n\n".join(context_parts)
        
        # Генерация ответа через Ollama
        prompt = SYSTEM_PROMPT.format(context=context, question=req.question)
        
        import httpx
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": "qwen2.5:3b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "max_tokens": 500
                    }
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama error: {response.status_code}")
            
            ollama_response = response.json()
            answer_text = ollama_response.get('response', '').strip()
        
        answer = {
            "answer": answer_text if answer_text else "Не удалось сгенерировать ответ. Попробуйте переформулировать вопрос.",
            "sources": sources[:3],  # Топ-3 источника
            "cached": False,
            "response_time": (datetime.now() - start_time).total_seconds()
        }
        
        # Кэширование
        redis_client.setex(cache_key, 3600, json.dumps(answer))
        
        logger.info(f"Ответ сгенерирован за {answer['response_time']:.2f}с")
        return answer
        
    except Exception as e:
        logger.error(f"Ошибка при обработке вопроса: {e}")
        return {
            "answer": f"Произошла ошибка при обработке вопроса: {str(e)}",
            "sources": [],
            "cached": False,
            "response_time": (datetime.now() - start_time).total_seconds()
        }

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
    
    try:
        from indexer import RepositoryScanner
        from chunker import CodeChunker
        
        scanner = RepositoryScanner()
        files = scanner.scan_files()
        
        logger.info(f"Найдено файлов для индексации: {len(files)}")
        
        # Получаем или создаём коллекцию
        collection = chroma_client.get_or_create_collection(
            name="pgr_docs",
            metadata={"description": "АСУ ПГР documentation and code"}
        )
        
        # Очищаем коллекцию при полной индексации
        if mode == "full":
            try:
                chroma_client.delete_collection("pgr_docs")
                collection = chroma_client.create_collection(
                    name="pgr_docs",
                    metadata={"description": "АСУ ПГР documentation and code"}
                )
                logger.info("Коллекция очищена для полной индексации")
            except:
                pass
        
        indexed_count = 0
        chunk_count = 0
        
        for file_info in files:
            try:
                # Читаем файл
                with open(file_info['full_path'], 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Разбиваем на чанки
                chunks = CodeChunker.chunk_file(file_info['path'], content)
                
                if not chunks:
                    continue
                
                # Добавляем в ChromaDB
                for chunk in chunks:
                    chunk_id = f"{file_info['path']}_{chunk_count}"
                    collection.add(
                        documents=[chunk['content']],
                        metadatas=[{
                            'file': file_info['path'],
                            'type': chunk.get('type', 'text'),
                            'line': chunk.get('line_start', 0)
                        }],
                        ids=[chunk_id]
                    )
                    chunk_count += 1
                
                indexed_count += 1
                
                if indexed_count % 10 == 0:
                    logger.info(f"Проиндексировано файлов: {indexed_count}/{len(files)}, чанков: {chunk_count}")
                    
            except Exception as e:
                logger.warning(f"Ошибка индексации файла {file_info['path']}: {e}")
                continue
        
        logger.info(f"Индексация завершена: {indexed_count} файлов, {chunk_count} чанков")
        
        return {
            "status": "completed",
            "mode": mode,
            "files_indexed": indexed_count,
            "chunks_created": chunk_count
        }
        
    except Exception as e:
        logger.error(f"Ошибка индексации: {e}")
        raise HTTPException(500, f"Ошибка индексации: {str(e)}")

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
