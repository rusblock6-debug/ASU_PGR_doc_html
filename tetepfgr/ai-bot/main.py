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
from sentence_transformers import SentenceTransformer

# Настройка логирования
os.makedirs("logs", exist_ok=True)
file_handler = RotatingFileHandler('logs/ai-bot.log', maxBytes=10_000_000, backupCount=5)
console_handler = logging.StreamHandler()
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
logger.info("Загрузка embedding модели...")
embedding_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', device='cuda' if __import__('torch').cuda.is_available() else 'cpu')
logger.info(f"Embedding модель загружена на устройстве: {embedding_model.device}")

class CustomEmbeddingFunction:
    """Custom embedding function compatible with ChromaDB 0.4.18"""
    def __init__(self):
        self.model = embedding_model
    
    def __call__(self, input):
        """ChromaDB expects this signature"""
        embeddings = self.model.encode(input, convert_to_numpy=True)
        return embeddings.tolist()

chroma_client = chromadb.PersistentClient(path="/app/chroma_data")

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)

API_KEY = os.getenv("API_KEY")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")

# Системный промпт для AI
SYSTEM_PROMPT = """# РОЛЬ И ЦЕЛЬ
Ты — технический писатель и инструктор для пользователей промышленной системы "АСУ ПГР".
Твоя задача: преобразовать техническую информацию из документации в понятную пошаговую инструкцию для обычного рабочего (не программиста).

# ОГРАНИЧЕНИЯ (STRICT CONSTRAINTS)
- ФОКУС: Только пользовательский интерфейс (кнопки, поля, меню).
- ЗАПРЕТЫ: Никаких упоминаний кода, API, файлов, баз данных, JSON, TS, JS, Python.
- ТОЧНОСТЬ: Не выдумывай функции, которых нет в контексте. Если информации нет — так и скажи.

# ДОКУМЕНТАЦИЯ (CONTEXT)
Используй только текст ниже для ответа. Не используй свои внешние знания.

{context}

# АЛГОРИТМ РАБОТЫ (THINKING PROCESS)
Перед тем как дать ответ, выполни следующие шаги (это внутренний монолог, не выводи его):
1. Анализ: Найди в контексте упоминания нужного раздела меню или формы.
2. Фильтрация: Отбрось всю техническую информацию (классы, ID, пути файлов).
3. Структурирование: Выстрой действия в хронологическом порядке (как это делает пользователь).
4. Проверка: Убедись, что все поля из формы перечислены.

# ФОРМАТ ВЫВОДА (OUTPUT FORMAT)
Строго следуй этой структуре. Не добавляй приветствий в начале и конца.

---
**Инструкция:**

Шаг 1: [Действие]
Шаг 2: [Действие]
...

**Обязательные поля:**
* `[Поле]`: [Тип] - [Описание/Особенности]

**Важные нюансы:**
* [Нюанс 1]
* [Нюанс 2]

**УВЕРЕННОСТЬ:** [0-100]%
---

# ПРИМЕРЫ (FEW-SHOT EXAMPLES)

Пример 1:
Вопрос: Как добавить нового сотрудника?

Ответ:
**Инструкция:**

Шаг 1: Перейдите в раздел "Управление персоналом" через боковую панель.
Шаг 2: Нажмите на кнопку "Новый сотрудник" (иконка плюса) в правом верхнем углу таблицы.
Шаг 3: Заполните открывшуюся форму.

**Обязательные поля:**
* `ФИО`: Текст - Вводится в формате "Фамилия Имя Отчество".
* `Должность`: Выпадающий список - Выберите из справочника должностей.

**Важные нюансы:**
* При вводе ФИО дубликаты автоматически подсвечиваются красным.

**УВЕРЕННОСТЬ:** 98%

---

Пример 2:
Вопрос: Как настроить backup базы данных?

Ответ:
В предоставленной документации отсутствуют инструкции по настройке резервного копирования базы данных. Обратитесь к администратору системы.

**УВЕРЕННОСТЬ:** 100%

---

# ТЕКУЩИЙ ЗАПРОС

История переписки:
{history}

Вопрос пользователя: {question}

Сформулируй ответ согласно ФОРМАТУ ВЫВОДА, используя данные из ДОКУМЕНТАЦИИ."""

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
            collection = chroma_client.get_collection(name="pgr_docs", embedding_function=CustomEmbeddingFunction())
        except:
            collection = chroma_client.get_or_create_collection(name="pgr_docs", embedding_function=CustomEmbeddingFunction())
        
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
        
        # Поиск похожих документов (уменьшено до 3 для ускорения)
        logger.info(f"⏱️ Начало поиска в ChromaDB...")
        search_start = datetime.now()
        results = collection.query(
            query_texts=[req.question],
            n_results=min(3, count)
        )
        search_time = (datetime.now() - search_start).total_seconds()
        logger.info(f"⏱️ Поиск завершен за {search_time:.2f} сек")
        
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
        
        # Формируем историю диалога если есть
        history_context = ""
        if req.history and len(req.history) > 0:
            history_messages = []
            for msg in req.history[-6:]:  # Берём последние 6 сообщений (3 пары вопрос-ответ)
                role = "Пользователь" if msg.get('role') == 'user' else "Ассистент"
                content = msg.get('content', '')
                history_messages.append(f"{role}: {content}")
            history_context = "\n".join(history_messages) + "\n\n"
        
        # Генерация ответа через Ollama (qwen3:8b)
        prompt = SYSTEM_PROMPT.format(
            context=context,
            question=req.question,
            history=history_context
        )
        
        logger.info(f"📝 Отправка запроса в Ollama (длина промпта: {len(prompt)} символов)")
        logger.info(f"❓ Вопрос: {req.question}")
        logger.info(f"📄 Контекст (первые 500 символов): {context[:500]}...")
        
        import httpx
        logger.info(f"⏱️ Начало запроса к Ollama...")
        ollama_start = datetime.now()
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": "qwen3:8b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "num_predict": 2000  # Увеличено для полных пошаговых инструкций
                    }
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama error: {response.status_code}")
            
            ollama_response = response.json()
            answer_text = ollama_response.get('response', '').strip()
        
        ollama_time = (datetime.now() - ollama_start).total_seconds()
        logger.info(f"⏱️ Ollama ответила за {ollama_time:.2f} сек")
        
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

@app.post("/api/index")
async def index_repository(
    mode: str = "full",
    snapshot: Optional[str] = None,
    x_api_key: Optional[str] = Header(None)
):
    """Индексация репозитория с гибридным чанкованием (параллельная обработка)"""
    verify_api_key(x_api_key)
    
    logger.info(f"Запуск индексации: mode={mode}, snapshot={snapshot}")
    
    try:
        import asyncio
        from src.indexer import RepositoryScanner
        from src.chunker import CodeChunker
        
        scanner = RepositoryScanner()
        files = scanner.scan_files()
        
        logger.info(f"Найдено файлов для индексации: {len(files)}")
        
        # Parse documentation JSON files
        doc_chunks = scanner.get_documentation_chunks()
        if doc_chunks:
            logger.info(f"📚 Documentation chunks: {len(doc_chunks)}")
        
        # Получаем или создаём коллекцию
        collection_name = "pgr_docs"
        
        # Очищаем коллекцию при полной индексации
        if mode == "full":
            try:
                # Удаляем старую коллекцию если существует
                try:
                    chroma_client.delete_collection(collection_name)
                    logger.info("Старая коллекция удалена")
                except:
                    logger.info("Коллекция не существовала, создаем новую")
                
                # Создаем новую коллекцию
                collection = chroma_client.create_collection(
                    name=collection_name,
                    metadata={"description": "АСУ ПГР documentation and code"},
                    embedding_function=CustomEmbeddingFunction()
                )
                logger.info("Новая коллекция создана для полной индексации")
            except Exception as e:
                logger.error(f"Ошибка при создании коллекции: {e}")
                raise HTTPException(500, f"Не удалось создать коллекцию: {str(e)}")
        else:
            # Для инкрементальной индексации получаем существующую коллекцию
            collection = chroma_client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "АСУ ПГР documentation and code"},
                embedding_function=CustomEmbeddingFunction()
            )
        
        indexed_count = 0
        chunk_count = 0
        qwen_chunked_count = 0
        
        # Функция обработки одного файла
        async def process_file(file_info):
            try:
                # Читаем файл
                with open(file_info['full_path'], 'r', encoding='utf-8-sig', errors='ignore') as f:
                    content = f.read()
                
                # Разбиваем на чанки (БЕЗ Qwen3 для быстрой индексации)
                chunks = await CodeChunker.chunk_file_async(file_info['path'], content, use_qwen=False)
                
                if not chunks:
                    return None
                
                # Считаем Qwen3 чанки
                qwen_chunks = [c for c in chunks if c.get('chunked_by') == 'qwen3']
                used_qwen = len(qwen_chunks) > 0
                
                if used_qwen:
                    logger.info(f"✨ Qwen3 обработал: {file_info['path']} ({len(qwen_chunks)} чанков)")
                
                return {
                    'file_info': file_info,
                    'chunks': chunks,
                    'used_qwen': used_qwen
                }
                    
            except Exception as e:
                logger.warning(f"Ошибка индексации файла {file_info['path']}: {e}")
                return None
        
        # Параллельная обработка батчами по 5 файлов
        BATCH_SIZE = 5
        for i in range(0, len(files), BATCH_SIZE):
            batch = files[i:i+BATCH_SIZE]
            
            # Обрабатываем батч параллельно
            results = await asyncio.gather(*[process_file(f) for f in batch])
            
            # Добавляем результаты в ChromaDB
            for result in results:
                if result is None:
                    continue
                
                file_info = result['file_info']
                chunks = result['chunks']
                
                if result['used_qwen']:
                    qwen_chunked_count += 1
                
                # Добавляем в ChromaDB
                for chunk in chunks:
                    chunk_id = f"{file_info['path']}_{chunk_count}"
                    collection.add(
                        documents=[chunk['content']],
                        metadatas=[{
                            'file': file_info['path'],
                            'type': chunk.get('type', 'text'),
                            'line': chunk.get('line_start', 0),
                            'chunked_by': chunk.get('chunked_by', 'tree-sitter')
                        }],
                        ids=[chunk_id]
                    )
                    chunk_count += 1
                
                indexed_count += 1
            
            # Логируем прогресс
            logger.info(f"📊 Прогресс: {indexed_count}/{len(files)} файлов, {chunk_count} чанков (Qwen3: {qwen_chunked_count})")
        
        # Add documentation chunks to ChromaDB
        if doc_chunks:
            logger.info(f"Adding {len(doc_chunks)} documentation chunks...")
            for doc_chunk in doc_chunks:
                chunk_id = f"doc_{chunk_count}"
                collection.add(
                    documents=[doc_chunk['content']],
                    metadatas=[{
                        'file': doc_chunk['metadata'].get('file', 'documentation'),
                        'type': doc_chunk['metadata'].get('type', 'documentation'),
                        'section': doc_chunk['metadata'].get('section', ''),
                        'source': doc_chunk['metadata'].get('source', 'JSON')
                    }],
                    ids=[chunk_id]
                )
                chunk_count += 1
            logger.info(f"✅ Documentation chunks added: {len(doc_chunks)}")
        
        logger.info(f"✅ Индексация завершена: {indexed_count} файлов, {chunk_count} чанков (вкл. {len(doc_chunks)} docs)")
        logger.info(f"✨ Qwen3 обработал: {qwen_chunked_count} файлов")
        
        return {
            "status": "completed",
            "mode": mode,
            "files_indexed": indexed_count,
            "chunks_created": chunk_count,
            "qwen_chunked_files": qwen_chunked_count
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
