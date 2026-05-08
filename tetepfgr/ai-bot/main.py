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

# Вставь этот код после импортов в main.py
BLUEPRINT_ARCHITECTURE = """# СИСТЕМНАЯ АРХИТЕКТУРА АСУ ПГР (STATIC BRAIN)
Используй эти знания, если в пользовательской документации нет прямого ответа.

## 1. Auth Service (auth-service-backend-dev)
**Назначение:** Пользователи, Роли, Разрешения.
**Ключевые API:**
- POST /api/signup (Регистрация), POST /api/login (Вход)
- GET /api/users, POST /api/users (CRUD Пользователей)
- GET /api/roles, POST /api/roles (CRUD Ролей и Прав доступа)
- GET /api/permissions (Список разрешений)
**Интерфейс:** Скорее всего находится в разделе "Администрирование" или "Настройки" -> "Пользователи".

## 2. Enterprise Service (enterprise-service-dev)
**Назначение:** Справочники и Наряд-задания.
**Ключевые API:**
- GET /api/vehicles, POST /api/vehicles (Техника/Самосвалы)
- GET /api/shift-tasks, POST /api/shift-tasks (Наряд-задания/Рейсы)
- GET /api/work-regimes (Смены/Режимы работы)
- GET /api/load-unload-points (Точки погрузки/разгрузки)
- GET /api/statuses (Справочник статусов: ремонт, обед, работа)
**Интерфейс:** Разделы "Оперативная работа" (Наряд-задания), "Справочники", "Управление парком".

## 3. Graph Service (graph-service-backend-dev)
**Назначение:** Карта, Дороги, 3D/2D визуализация.
**Ключевые API:**
- GET /api/levels (Горизонты карьера)
- GET /api/nodes, GET /api/edges (Узлы и Дороги - схема)
- POST /api/location/find (Поиск по GPS координатам)
- GET /api/route/{start}/{end} (Построение маршрута)
**Интерфейс:** Раздел "Карта", "Визуализация". Поддержка 2D (плоская карта) и 3D (рельеф).

## 4. Analytics Service (analytics-service-dev)
**Назначение:** Аналитика, Отчеты, КРВ (Коэффициент использования).
**Ключевые API:**
- POST /api/vehicle-telemetry (Данные телеметрии)
- ETL процессы для отчетов.
**Интерфейс:** Раздел "Отчеты", "Аналитика", "Мониторинг производительности".

## 5. Trip Service (dispa-backend-dev)
**Назначение:** Бортовое управление рейсами, State Machine (состояние техники).
**Ключевые API:**
- GET /api/tasks (Задания на смену)
- POST /api/trips/{id}/start (Начать рейс)
**Интерфейс:** Бортовой терминал (Bort Client) и панель диспетчера.

## ФРОНТЕНД СТРУКТУРА (client-disp-dev)
**Основные страницы:**
- dispatch-map (Карта диспетчера)
- work-order (Наряд-задания)
- fleet-control (Управление техникой)
- trip-editor (Редактор рейсов)
- settings (Настройки)
- staff (Персонал)
- cargo (Виды груза)

## ПРИНЦИП ВЫВОДА (INFERENCE)
Если пользователь спрашивает "Как создать роль?", а инструкции нет:
1. Видим в Auth Service есть POST /api/roles.
2. Догадываемся: Значит, интерфейс должен иметь форму создания роли в разделе Администрирования.
3. Отвечаем с предположением, указывая низкую уверенность."""

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
embedding_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', device='cpu')
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
SYSTEM_PROMPT = """# РОЛЬ
Ты — Технический Эксперт АСУ ПГР. Твоя главная задача — давать точные ответы, основываясь на качестве найденных данных.

# ДАННЫЕ
1. **Архитектура (База):**
{blueprint}

2. **Документация (Результаты поиска):**
Качество поиска: {search_quality} (Средняя дистанция: {avg_distance})
{context}

# ЛОГИКА УВЕРЕННОСТИ И ИСПОЛЬЗОВАНИЯ КОНТЕКСТА

## Если search_quality == "HIGH" (Дистанция < 0.3)
Найденные документы СОВЕРШЕННО совпадают с вопросом.
- **Действие:** Используй документы для точного ответа.
- **Уверенность:** Ставь 90-100%.
- **Источник:** "Документация".

## Если search_quality == "MEDIUM" (Дистанция 0.3 - 0.5)
Документы частично подходят, но могут содержать лишнюю информацию.
- **Действие:** Используй документы, но фильтруй лишнее. Если точных шагов нет, используй Архитектуру для дополнения.
- **Уверенность:** Ставь 60-80%.
- **Источник:** "Документация + Дополнение".

## Если search_quality == "LOW" (Дистанция > 0.5)
**ВНИМАНИЕ:** Поиск вернул МУСОР (нерелевантные чанки). Вопрос пользователя содержал сленг или нечеткие формулировки, которые исказили семантический поиск.
- **СТРОГОЕ ЗАПРЕЩЕНИЕ:** НЕ ИСПОЛЬЗУЙ блок "Документация (Результаты поиска)". Это приведет к галлюцинациям.
- **Действие:** 
  1. Игнорируй найденные чанки.
  2. Попробуй найти ответ в **Архитектуре (Blueprint)**.
  3. Если и там нет — вежливо откажись.
- **Уверенность:** Ставь 0-30% (если отвечаешь по архитектуре) или 0% (если отказ).

# ШАБЛОН ОТВЕТА
---
**Ответ:**
[Сформулируй ответ согласно логике выше]

**Анализ данных:**
- Качество поиска: {search_quality}
- Используемый источник: [Документы / Архитектура / Отказ]

**Уверенность:** [Число]% (Ставь честно, опираясь на search_quality)
---

# ВОПРОС
{question}"""

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
    search_quality: Optional[str] = None  # HIGH / MEDIUM / LOW
    avg_distance: Optional[float] = None  # Средняя дистанция поиска

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
    
    # Базовая проверка на явный оффтоп (быстрая, без тормозов)
    question_lower = req.question.lower()
    
    # Только самые явные стоп-слова
    if any(word in question_lower for word in ['украина', 'россия', 'война', 'политика', 'выборы']):
        logger.warning(f"⛔ Заблокирован политический вопрос: {req.question}")
        return {
            "answer": "Я отвечаю только на вопросы по системе АСУ ПГР.",
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
        # --- НАЧАЛО ИЗМЕНЕНИЙ В /api/ask ---
        # Получаем коллекцию
        try:
            collection = chroma_client.get_collection(name="pgr_docs", embedding_function=CustomEmbeddingFunction())
        except:
            collection = chroma_client.get_or_create_collection(name="pgr_docs", embedding_function=CustomEmbeddingFunction())
        
        count = collection.count()
        if count == 0:
            return {
                "answer": "База знаний пуста.",
                "sources": [],
                "cached": False,
                "response_time": (datetime.now() - start_time).total_seconds()
            }
        
        # 1. ИЗМЕНЯЕМ ЗАПРОС К CHROMADB
        # Добавляем include=['distances'], чтобы получить оценки сходства
        # Увеличиваем n_results до 15, чтобы больше шансов найти что-то стоящее
        logger.info(f"⏱️ Начало поиска в ChromaDB...")
        results = collection.query(
            query_texts=[req.question],
            n_results=min(15, count),
            include=['documents', 'metadatas', 'distances']  # <--- ВАЖНО: Добавь distances
        )
        logger.info(f"⏱️ Поиск завершен")
        
        # 2. РАСЧЕТ КАЧЕСТВА ПОИСКА (MATH LOGIC)
        if not results['documents'] or not results['documents'][0]:
            context_text = "Поиск в документации не дал результатов."
            sources = []
            avg_distance = 1.0  # Максимум (худший случай)
        else:
            # Берем дистанции (scores) для топ-3 результатов
            distances = results['distances'][0]
            top_distances = distances[:3]
            
            # Считаем среднюю дистанцию (чем меньше, тем лучше)
            avg_distance = sum(top_distances) / len(top_distances)
            
            # Формируем текст контекста
            context_parts = []
            sources = []
            for i, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i]
                dist = results['distances'][0][i]
                
                # Добавляем Score в текст, чтобы модель видела точность совпадения
                context_parts.append(f"[Source {i+1} (Score: {dist:.4f})]: {doc}")
                sources.append({
                    "file": metadata.get('file'),
                    "score": round(dist, 4),  # Возвращаем score в ответ API
                    "type": metadata.get('type')
                })
            
            context_text = "\n\n".join(context_parts)
        
        # 3. ОПРЕДЕЛЯЕМ КАТЕГОРИЮ КАЧЕСТВА (HIGH / MEDIUM / LOW)
        # Cosine Distance: 0 = идеально, >0.5 = плохо
        if avg_distance < 0.3:
            search_quality = "HIGH"
        elif avg_distance < 0.5:
            search_quality = "MEDIUM"
        else:
            search_quality = "LOW"
        
        logger.info(f"📊 Качество поиска: {search_quality} (Avg Dist: {avg_distance:.4f})")
        
        # Формируем историю диалога
        history_context = ""
        if req.history and len(req.history) > 0:
            history_messages = []
            for msg in req.history[-6:]:
                role = "Пользователь" if msg.get('role') == 'user' else "Ассистент"
                content = msg.get('content', '')
                history_messages.append(f"{role}: {content}")
            history_context = "\n".join(history_messages) + "\n\n"
        
        # 4. ФОРМИРУЕМ ПРОМПТ С НОВЫМИ ПЕРЕМЕННЫМИ
        prompt = SYSTEM_PROMPT.format(
            blueprint=BLUEPRINT_ARCHITECTURE,  # Передаем архитектуру
            context=context_text,              # Передаем чанки с score
            question=req.question,
            history=history_context,
            search_quality=search_quality,     # Передаем качество
            avg_distance=f"{avg_distance:.4f}" # Передаем число
        )
        # --- КОНЕЦ ИЗМЕНЕНИЙ В /api/ask ---
        
        logger.info(f"📝 Отправка запроса в Ollama (длина промпта: {len(prompt)} символов)")
        logger.info(f"❓ Вопрос: {req.question}")
        logger.info(f"📄 Контекст (первые 500 символов): {context_text[:500]}...")
        
        import httpx
        logger.info(f"⏱️ Начало запроса к Ollama...")
        ollama_start = datetime.now()
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": "phi4-mini",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # <--- ОБЯЗАТЕЛЬНО 0.1 (Снижает фантазии)
                        "top_p": 0.9,
                        "num_predict": 2000,
                        "repeat_penalty": 1.1
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
        
        # Логируем сырой ответ для отладки
        logger.info(f"📝 Сырой ответ модели (первые 500 символов): {answer_text[:500]}")
        
        # Ищем секцию УВЕРЕННОСТЬ (поддерживаем разные форматы)
        import re
        # Формат 1: **Уверенность:** 90%
        confidence_match = re.search(r'\*\*Уверенность:\*\*\s*(\d+)%', answer_text, re.IGNORECASE)
        if not confidence_match:
            # Формат 2: УВЕРЕННОСТЬ: 90%
            confidence_match = re.search(r'УВЕРЕННОСТЬ:\s*(\d+)%', answer_text, re.IGNORECASE)
        if not confidence_match:
            # Формат 3: Уверенность: 90%
            confidence_match = re.search(r'Уверенность:\s*(\d+)%', answer_text, re.IGNORECASE)
        
        if confidence_match:
            confidence = int(confidence_match.group(1))
            logger.info(f"✅ Найдена уверенность: {confidence}%")
            # Удаляем секции метаданных из ответа
            clean_answer = re.sub(r'\n*\*\*Уверенность:\*\*.*', '', answer_text, flags=re.IGNORECASE)
            clean_answer = re.sub(r'\n*УВЕРЕННОСТЬ:.*', '', clean_answer, flags=re.IGNORECASE)
            clean_answer = re.sub(r'\n*\*\*Анализ данных:\*\*.*', '', clean_answer, flags=re.IGNORECASE | re.DOTALL)
            clean_answer = re.sub(r'\n*ИСПОЛЬЗОВАННЫЕ ИСТОЧНИКИ:.*', '', clean_answer, flags=re.IGNORECASE | re.DOTALL)
            clean_answer = clean_answer.strip()
        else:
            logger.warning(f"⚠️ Уверенность не найдена в ответе модели")
        
        answer = {
            "answer": clean_answer if clean_answer else "Не удалось сгенерировать ответ. Попробуйте переформулировать вопрос.",
            "sources": sources[:3],  # Топ-3 источника
            "cached": False,
            "response_time": (datetime.now() - start_time).total_seconds(),
            "confidence": confidence,
            "search_quality": search_quality,  # Добавляем качество поиска в ответ
            "avg_distance": round(avg_distance, 4)  # Добавляем среднюю дистанцию
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
        phi4_chunked_count = 0
        
        # Функция обработки одного файла
        async def process_file(file_info):
            try:
                # Читаем файл
                with open(file_info['full_path'], 'r', encoding='utf-8-sig', errors='ignore') as f:
                    content = f.read()
                
                # Разбиваем на чанки (БЕЗ Phi-4 для быстрой индексации)
                chunks = await CodeChunker.chunk_file_async(file_info['path'], content, use_phi4=False)
                
                if not chunks:
                    return None
                
                # Считаем Phi-4 чанки
                phi4_chunks = [c for c in chunks if c.get('chunked_by') == 'phi4-mini']
                used_phi4 = len(phi4_chunks) > 0
                
                if used_phi4:
                    logger.info(f"✨ Phi-4 обработал: {file_info['path']} ({len(phi4_chunks)} чанков)")
                
                return {
                    'file_info': file_info,
                    'chunks': chunks,
                    'used_phi4': used_phi4
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
                
                if result['used_phi4']:
                    phi4_chunked_count += 1
                
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
            logger.info(f"📊 Прогресс: {indexed_count}/{len(files)} файлов, {chunk_count} чанков (Phi-4: {phi4_chunked_count})")
        
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
        logger.info(f"✨ Phi-4 обработал: {phi4_chunked_count} файлов")
        
        return {
            "status": "completed",
            "mode": mode,
            "files_indexed": indexed_count,
            "chunks_created": chunk_count,
            "phi4_chunked_files": phi4_chunked_count
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
