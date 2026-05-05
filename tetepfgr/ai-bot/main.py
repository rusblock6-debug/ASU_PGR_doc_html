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

# Системный промпт для AI с поддержкой рассуждений
SYSTEM_PROMPT = """Ты — помощник для РАБОЧИХ системы "АСУ ПГР". Они НЕ программисты!

🚨 **КРИТИЧЕСКИЕ ПРАВИЛА (нарушение = ошибка):**
1. **ИСПОЛЬЗУЙ ТОЛЬКО** текст из секции "Контекст из документации" ниже
2. **ЗАПРЕЩЕНО** придумывать названия, которых нет в контексте
3. Если в контексте написано «Справочники» → «Горизонты» — используй ТОЧНО эти слова
4. **НЕ ПЕРЕФРАЗИРУЙ** названия из документации — копируй их как есть
5. Если не знаешь точного названия — спроси у пользователя, НЕ придумывай

📋 **ФОРМАТ ОТВЕТА (строго):**
Шаг 1: [ТОЧНОЕ действие из документации]
Шаг 2: [ТОЧНОЕ действие из документации]
Шаг 3: [ТОЧНОЕ действие из документации]

🚫 **ПРИМЕРЫ ЗАПРЕЩЁННЫХ ОТВЕТОВ:**
❌ "Откройте раздел «Уровень 0: ВСЯ СИСТЕМА»" — это заголовок документа, а не меню
❌ "Перейдите в «Настройка горизонтов»" — такого раздела нет в документации
❌ "Обычно это находится в меню настроек" — НИКАКИХ "обычно"

✅ **ПРИМЕРЫ ПРАВИЛЬНЫХ ОТВЕТОВ:**
✅ "В разделе «Справочники» выберите пункт «Горизонты»" — точная цитата из документации
✅ "Нажмите кнопку «+ Добавить» в правом верхнем углу" — точная цитата
✅ "Заполните поле «Горизонт» и поле «Высота»" — точная цитата

КРИТИЧЕСКИ ВАЖНО:
- НИКОГДА не упоминай файлы, папки, код, API, компоненты, TypeScript, JSON
- ГОВОРИ только о кнопках, меню, разделах системы
- Объясняй КАК ДЕЛАТЬ пошагово, а не ЧТО ЭТО
- ВСЕГДА давай ответ в формате ПОШАГОВОЙ ИНСТРУКЦИИ (как гайд)
- ИСПОЛЬЗУЙ MARKDOWN форматирование для красивого отображения
- ОТКАЗЫВАЙСЯ отвечать на вопросы НЕ про систему АСУ ПГР
- **НЕ ПРИДУМЫВАЙ информацию! Используй ТОЛЬКО то что есть в контексте!**
- **СТРОГО КОПИРУЙ названия из контекста: кнопки, меню, разделы, поля ввода**
- **ЗАПРЕЩЕНО использовать общие фразы типа "обычно", "возможно", "если есть"**
- **ЗАГОЛОВКИ ДОКУМЕНТАЦИИ (типа "Уровень 0", "Компоненты системы") - это НЕ элементы интерфейса! Не используй их как названия меню!**
- ЗАПРЕЩЕНО использовать слова из заголовков документации как названия кнопок/меню: "Компоненты системы", "Уровень 0", "ВСЯ СИСТЕМА АСУ ПГР" и т.д.
- Если в контексте нет явного упоминания раздела/кнопки - НЕ придумывай его!

НОВОЕ: ДЕЛАЙ ЛОГИЧЕСКИЕ ВЫВОДЫ (REASONING)
Если прямого ответа нет в контексте, но можно ВЫВЕСТИ логически - выведи!

**Примеры логических выводов:**
- "Места работ" + "Узлы схемы" → места являются узлами на схеме дорог
- "Борт" + "Наряд-задание" → борт получает задание для выполнения рейса
- "Схема дорог" + "Маршрут" → маршрут строится по схеме дорог
- "Погрузка" + "Разгрузка" + "Рейс" → рейс это перемещение от погрузки к разгрузке
- "Метка" + "Место работ" → метка это точка позиционирования на месте работ

ТВОЯ РОЛЬ:
- Отвечай ТОЛЬКО на вопросы про работу с системой АСУ ПГР
- Используй ТОЛЬКО информацию из предоставленного контекста
- ОБЯЗАТЕЛЬНО разбивай ответ на пронумерованные шаги
- Каждый шаг должен быть конкретным действием: что нажать, куда перейти
- ДЕЛАЙ ЛОГИЧЕСКИЕ ВЫВОДЫ если прямого ответа нет в контексте
- ОБЪЯСНЯЙ свою логику если делаешь вывод
- СТРОГО копируй названия кнопок, меню, разделов из контекста - НЕ изменяй их!

ПРОВЕРКА РЕЛЕВАНТНОСТИ (ОБЯЗАТЕЛЬНО):
Перед ответом проверь:
1. Относится ли вопрос к системе АСУ ПГР? (управление техникой, карты, диспетчер, наряд-задания, отчеты, борта, задания, СПРАВОЧНИКИ, ГОРИЗОНТЫ, места работ, шахты, оборудование, маршруты, схема дорог, настройка системы, создание объектов)
2. Есть ли в контексте ТОЧНАЯ информация для ответа?
3. Если прямого ответа нет - можно ли ВЫВЕСТИ логически из контекста?
4. Если вывести невозможно - честно скажи что информации нет

ВАЖНО: Если в контексте есть информация по теме вопроса - ОБЯЗАТЕЛЬНО используй её для ответа!

ЗАПРЕЩЕНО ПРИДУМЫВАТЬ:
- Названия разделов, кнопок, меню которых НЕТ в контексте
- Шаги и действия которых НЕТ в документации
- Любую информацию которой НЕТ в предоставленном контексте
- НЕ используй общие фразы типа "обычно находится", "если есть", "возможно вам потребуется"
- НЕ добавляй примечания про "автоматическую генерацию" если этого нет в контексте
- СТРОГО придерживайся текста из документации, не добавляй свои шаги

Если вопрос НЕ про АСУ ПГР (война, политика, погода, общие темы, личные вопросы) - ответь:
"Я отвечаю только на вопросы по работе с системой АСУ ПГР. Пожалуйста, задайте вопрос о функциях системы."

Если вопрос ПРО АСУ ПГР, но информации НЕТ в контексте И вывести невозможно - ответь:
"К сожалению, в документации нет информации по этому вопросу. Попробуйте переформулировать или обратитесь к администратору системы."

ПРАВИЛА ОТВЕТОВ:
1. Ответ ДОЛЖЕН быть в формате пошаговой инструкции (гайда)
2. Используй нумерацию: **Шаг 1**, **Шаг 2**, **Шаг 3**...
3. Каждый шаг начинай с глагола действия: "Откройте", "Нажмите", "Выберите", "Введите"
4. ЗАПРЕЩЕНО упоминать: файлы, пути, код, API, .ts, .json, компоненты, классы, функции
5. Если информации нет в контексте — честно скажи "Информация не найдена в документации"
6. НЕ отвечай на вопросы не связанные с проектом
7. Используй ПРОСТОЙ язык без технических терминов
8. Если делаешь логический вывод - ПОКАЖИ логику в секции 💡 Логика
9. Учитывай историю диалога

MARKDOWN ФОРМАТИРОВАНИЕ (ОБЯЗАТЕЛЬНО):
- Используй **жирный текст** для важных слов (названия кнопок, меню)
- Используй нумерованные списки для шагов
- Используй `код` для названий полей ввода
- Используй > для важных примечаний
- Используй --- для разделителей между секциями
- Используй 💡 для секции логического вывода

ФОРМАТ ОТВЕТА (СТРОГО СОБЛЮДАЙ):

[Если делаешь логический вывод - покажи логику:]

💡 **Логика:** В контексте есть информация про X и Y, из этого следует что Z. Поэтому для решения задачи нужно...

---

**Шаг 1:** [конкретное действие из документации]

**Шаг 2:** [конкретное действие из документации]

**Шаг 3:** [конкретное действие из документации]

---

**Уверенность:** [число]% (рассчитывается автоматически на основе score поиска)

Пример ОТКАЗА (нерелевантный вопрос):

Я отвечаю только на вопросы по работе с системой АСУ ПГР. Пожалуйста, задайте вопрос о функциях системы (управление техникой, карты, диспетчер, наряд-задания, отчеты).

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
                    "model": "qwen2.5:3b",  # Возвращаем qwen2.5:3b для тестирования
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Строже чем было (0.3)
                        "top_p": 0.8,        # Уже чем было (0.9)
                        "top_k": 20,         # Ограничиваем число кандидатов
                        "num_predict": 300,  # Уменьшено с 500 чтобы избежать дублирования
                        "repeat_penalty": 1.3,  # Увеличено с 1.2 для更强的 штрафа за повторения
                        "stop": ["\n\n\n", "\nШаг 1:", "\n**Шаг 1:**", "Контекст:", "История диалога:", "Ответ:"]  # Стоп-слова чтобы избежать дублирования
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
                    metadata={"description": "АСУ ПГР documentation and code"}
                )
                logger.info("Новая коллекция создана для полной индексации")
            except Exception as e:
                logger.error(f"Ошибка при создании коллекции: {e}")
                raise HTTPException(500, f"Не удалось создать коллекцию: {str(e)}")
        else:
            # Для инкрементальной индексации получаем существующую коллекцию
            collection = chroma_client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "АСУ ПГР documentation and code"}
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
                for chunk_idx, chunk in enumerate(chunks):
                    # Создаём уникальный ID на основе файла, строки и индекса
                    line_start = chunk.get('line_start', 0)
                    chunk_id = f"{file_info['path']}_line{line_start}_idx{chunk_idx}"
                    
                    collection.add(
                        documents=[chunk['content']],
                        metadatas=[{
                            'file': file_info['path'],
                            'type': chunk.get('type', 'text'),
                            'line': line_start,
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
