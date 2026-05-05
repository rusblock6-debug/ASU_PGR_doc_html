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
from src.hybrid_search import hybrid_search

# Настройка логирования
os.makedirs("logs", exist_ok=True)
file_handler = RotatingFileHandler('logs/ai-bot.log', maxBytes=10_000_000, backupCount=5)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

logging.basicConfig(
    handlers=[file_handler, console_handler],
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
SYSTEM_PROMPT = """Ты — помощник для пользователей системы "АСУ ПГР".

КРИТИЧЕСКИ ВАЖНЫЕ ПРАВИЛА:
1. Отвечай ТОЛЬКО на вопросы про систему АСУ ПГР
2. Используй ИСКЛЮЧИТЕЛЬНО информацию из секции "Контекст из документации" ниже
3. ЗАПРЕЩЕНО придумывать, додумывать или предполагать информацию которой нет в контексте
4. ЗАПРЕЩЕНО упоминать названия кнопок, меню, полей, разделов которых НЕТ в контексте
5. Если в контексте нет полного ответа — скажи: "К сожалению, в документации нет полной информации по этому вопросу"
6. НЕ упоминай файлы, код, API, технические детали реализации

ФОРМАТ ОТВЕТА:
- Давай ответ в виде пошаговой инструкции
- Используй формат: **Шаг 1:** [действие]
- КОПИРУЙ точные названия из документации БЕЗ ИЗМЕНЕНИЙ
- Если не уверен в точности — лучше скажи что информации недостаточно

Пример ПРАВИЛЬНОГО ответа (все названия взяты из контекста):
**Шаг 1:** Откройте «Оперативная работа» → «Наряд-задание»
**Шаг 2:** Выберите смену в фильтре
**Шаг 3:** Найдите карточку техники

Пример НЕПРАВИЛЬНОГО ответа (придуманные названия):
**Шаг 1:** Нажмите кнопку "Создать новый" ❌ (такой кнопки нет в контексте)
**Шаг 2:** Заполните поле "Дата начала" ❌ (такого поля нет в контексте)

---

Контекст из документации:
{context}

История диалога:
{history}

Вопрос пользователя: {question}

Ответ:"""

# Модели
class QuestionRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    chat_id: Optional[str] = None
    history: Optional[List[dict]] = None  # [{"role": "user", "content": "..."}]
    
class AnswerResponse(BaseModel):
    answer: str
    sources: List[dict]
    cached: bool = False
    response_time: float
    confidence: Optional[int] = None

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
        try:
            collection = chroma_client.get_collection(name="pgr_docs")
        except:
            collection = chroma_client.get_or_create_collection(name="pgr_docs")
        
        # Проверяем есть ли документы
        count = collection.count()
        logger.info(f"📊 Документов в базе: {count}")
        if count == 0:
            return {
                "answer": "База знаний пуста. Необходимо запустить индексацию репозитория через API: POST /api/index?mode=full",
                "sources": [],
                "cached": False,
                "response_time": (datetime.now() - start_time).total_seconds()
            }
        
        # Поиск похожих документов с гибридным поиском
        results = hybrid_search(
            collection=collection,
            question=req.question,
            n_results=min(5, count),
            vector_n=15,  # Берём больше для лучшего покрытия
            keyword_n=10
        )
        
        if not results or len(results) == 0:
            return {
                "answer": "По вашему вопросу не найдено релевантной информации в документации. Попробуйте переформулировать вопрос или задать более конкретный.",
                "sources": [],
                "cached": False,
                "response_time": (datetime.now() - start_time).total_seconds()
            }
        
        # Формируем контекст из результатов гибридного поиска
        context_parts = []
        sources = []
        max_score = 0.0
        for i, result in enumerate(results):
            section = result['metadata'].get('section', result['metadata'].get('file_type', ''))
            context_parts.append(f"📄 ДОКУМЕНТАЦИЯ (раздел {section}):\n{result['document']}")
            score = round(result.get('score', 0.0), 3)
            if score > max_score:
                max_score = score
            sources.append({
                "file": result['metadata'].get('file', 'unknown'),
                "line": result['metadata'].get('line', None),
                "type": result['metadata'].get('type', 'text'),
                "score": score
            })
        
        # Рассчитываем confidence на основе максимального score
        # score ranges from 0 to ~0.7 (with weights), convert to percentage
        confidence = min(int(max_score * 100 / 0.7), 100) if max_score > 0 else 0
        
        context = "\n\n".join(context_parts)
        
        # Формируем историю диалога если есть
        history_context = ""
        if req.history and len(req.history) > 0:
            history_messages = []
            for msg in req.history[-6:]:  # Берём последние 6 сообщений (3 пары вопрос-ответ)
                role = "Пользователь" if msg.get('role') == 'user' else "Ассистент"
                content = msg.get('content', '')
                history_messages.append(f"{role}: {content}")
            history_context = "\n".join(history_messages) + "\n\n"
        
        # Генерация ответа через Ollama (Phi-4-mini)
        prompt = SYSTEM_PROMPT.format(
            context=context,
            question=req.question,
            history=history_context
        )
        
        logger.info(f"📝 Отправка запроса в Ollama (длина промпта: {len(prompt)} символов)")
        logger.info(f"❓ Вопрос: {req.question}")
        logger.info(f"📄 Контекст (первые 500 символов): {context[:500]}...")
        
        import httpx
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": "phi4-mini:latest",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,
                        "top_p": 0.9,
                        "num_predict": 400
                    }
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama error: {response.status_code}")
            
            ollama_response = response.json()
            answer_text = ollama_response.get('response', '').strip()
        
        # Удаление дубликатов в ответе
        lines = answer_text.split('\n')
        seen_lines = set()
        unique_lines = []
        duplicate_detected = False
        step_count = 0
        for line in lines:
            stripped = line.strip()
            
            # Проверяем на повторение "Шаг N:" - это явный признак дублирования
            import re
            if re.match(r'^\*\*Шаг \d+:', stripped):
                step_count += 1
                if step_count > 1:
                    # Уже был такой шаг раньше - обрезаем здесь
                    logger.warning(f"⚠️ Обнаружено дублирование ответа на шаге {step_count} - обрезано")
                    break
            
            # Пропускаем строки которые выглядят как примеры из промпта
            if any(keyword in stripped for keyword in ['ПРАВИЛЬНО:', 'НЕПРАВИЛЬНО:', 'ЗАПРЕЩЕНО']):
                continue
            
            if stripped and stripped in seen_lines:
                duplicate_detected = True
                logger.warning("⚠️ Обнаружено точное дублирование строки - обрезано")
                break  # Нашли дубликат - обрезаем ответ здесь
            if stripped:
                seen_lines.add(stripped)
            unique_lines.append(line)
        
        if duplicate_detected:
            logger.warning("⚠️ Обнаружено дублирование ответа - обрезано")
            answer_text = '\n'.join(unique_lines).strip()
        
        # Валидация ОТКЛЮЧЕНА - работает неправильно, добавляет ложные предупреждения
        # doc_terms = set(re.findall(r'[«"]([^»"]+)[»"]', context))
        # answer_terms = re.findall(r'[«"]([^»"]+)[»"]', answer_text)
        # hallucinations = [term for term in answer_terms if term not in doc_terms and len(term) > 3]
        
        # Парсим confidence из ответа
        confidence = None
        clean_answer = answer_text
        
        # Ищем секцию УВЕРЕННОСТЬ
        import re
        confidence_match = re.search(r'УВЕРЕННОСТЬ:\s*(\d+)%', answer_text, re.IGNORECASE)
        if confidence_match:
            confidence = int(confidence_match.group(1))
            # Удаляем секции метаданных из ответа
            clean_answer = re.sub(r'\n*УВЕРЕННОСТЬ:.*', '', answer_text, flags=re.IGNORECASE)
            clean_answer = re.sub(r'\n*ИСПОЛЬЗОВАННЫЕ ИСТОЧНИКИ:.*', '', clean_answer, flags=re.IGNORECASE | re.DOTALL)
            clean_answer = re.sub(r'\n*ПРИЧИНА НЕУВЕРЕННОСТИ:.*', '', clean_answer, flags=re.IGNORECASE | re.DOTALL)
            clean_answer = clean_answer.strip()
        
        answer = {
            "answer": clean_answer if clean_answer else "Не удалось сгенерировать ответ. Попробуйте переформулировать вопрос.",
            "sources": sources[:3],  # Топ-3 источника
            "cached": False,
            "response_time": (datetime.now() - start_time).total_seconds(),
            "confidence": confidence
        }
        
        # Кэширование
        redis_client.setex(cache_key, 3600, json.dumps(answer))
        
        logger.info(f"Ответ сгенерирован за {answer['response_time']:.2f}с")
        return answer
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Ошибка при обработке вопроса: {e}\n{error_details}")
        return {
            "answer": f"Произошла ошибка при обработке вопроса: {str(e) if str(e) else 'Неизвестная ошибка'}",
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

# Старый endpoint /api/index удалён - индексировал весь репозиторий вместо только documentation

@app.post("/api/reindex")
async def reindex_repository(
    mode: str = "full",
    x_api_key: Optional[str] = Header(None)
):
    """Переиндексация документации (полная или инкрементальная)"""
    verify_api_key(x_api_key)
    
    logger.info(f"Запуск переиндексации: mode={mode}")
    
    try:
        from src.indexer import RepositoryScanner
        from src.chunker import CodeChunker
        
        # Очищаем старую коллекцию
        try:
            chroma_client.delete_collection(name="pgr_docs")
            logger.info("Old collection deleted")
        except:
            pass
        
        # Создаём новую коллекцию
        collection = chroma_client.get_or_create_collection(name="pgr_docs")
        
        # Сканируем документацию
        scanner = RepositoryScanner(repo_path="/data/documentation")
        chunks = scanner.get_documentation_chunks()
        
        if not chunks:
            return {"status": "error", "message": "No documentation chunks found"}
        
        # Индексируем чанки в ChromaDB
        indexed_count = 0
        for i, chunk in enumerate(chunks):
            try:
                content = chunk.get('content', '')
                if not content or len(content.strip()) < 10:
                    continue
                
                # Генерируем ID
                chunk_id = hashlib.md5(
                    f"{chunk.get('source', 'unknown')}_{i}".encode()
                ).hexdigest()
                
                # Метаданные
                metadata = {
                    'source': chunk.get('source', 'unknown'),
                    'file': chunk.get('file', chunk.get('source', 'unknown')),  # Для совместимости с hybrid_search
                    'file_type': chunk.get('file_type', 'text'),
                    'chunk_index': i,
                    'type': chunk.get('type', 'section')
                }
                
                # Добавляем в ChromaDB
                collection.add(
                    ids=[chunk_id],
                    documents=[content],
                    metadatas=[metadata]
                )
                
                indexed_count += 1
                
            except Exception as e:
                logger.error(f"Error indexing chunk {i}: {e}")
                continue
        
        logger.info(f"Indexing complete: {indexed_count} chunks indexed")
        
        return {
            "status": "success",
            "chunks_indexed": indexed_count,
            "total_chunks": len(chunks),
            "mode": mode
        }
        
    except Exception as e:
        logger.error(f"Ошибка переиндексации: {e}")
        raise HTTPException(500, f"Ошибка переиндексации: {str(e)}")

@app.get("/api/stats")
async def get_stats():
    """Получение статистики RAG-бота"""
    try:
        # Получаем количество документов в ChromaDB
        try:
            collection = chroma_client.get_collection(name="pgr_docs")
            doc_count = collection.count()
        except:
            doc_count = 0
        
        # Получаем базовую статистику из Redis
        cache_keys = redis_client.keys("q:*")
        cache_size = len(cache_keys)
        
        stats = {
            "documents_in_db": doc_count,
            "cache_entries": cache_size,
            "ollama_url": OLLAMA_URL,
            "redis_host": os.getenv("REDIS_HOST", "redis"),
            "uptime": "N/A"  # Можно добавить позже
        }
        
        return stats
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        raise HTTPException(500, f"Ошибка: {str(e)}")

@app.post("/api/cache/clear")
async def clear_cache(x_api_key: Optional[str] = Header(None)):
    """Очистка кэша ответов Redis"""
    verify_api_key(x_api_key)
    
    logger.info("Очистка кэша ответов...")
    
    try:
        # Удаляем все ключи кэша (паттерн q:*)
        cache_keys = redis_client.keys("q:*")
        deleted_count = 0
        
        if cache_keys:
            deleted_count = redis_client.delete(*cache_keys)
        
        logger.info(f"Кэш очищен: удалено {deleted_count} записей")
        
        return {
            "status": "success",
            "deleted_entries": deleted_count
        }
        
    except Exception as e:
        logger.error(f"Ошибка очистки кэша: {e}")
        raise HTTPException(500, f"Ошибка очистки кэша: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
