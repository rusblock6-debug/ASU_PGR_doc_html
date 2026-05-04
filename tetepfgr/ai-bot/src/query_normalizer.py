"""
Нормализация поисковых запросов для улучшения качества поиска
"""
import re
import json
from pathlib import Path
from typing import Dict, List, Set

# Загружаем словарь синонимов
SYNONYMS_PATH = Path(__file__).parent / "synonyms.json"
with open(SYNONYMS_PATH, 'r', encoding='utf-8') as f:
    SYNONYMS: Dict[str, List[str]] = json.load(f)

# Создаём обратный индекс: синоним -> основной термин
REVERSE_SYNONYMS: Dict[str, str] = {}
for main_term, synonyms in SYNONYMS.items():
    REVERSE_SYNONYMS[main_term] = main_term
    for synonym in synonyms:
        REVERSE_SYNONYMS[synonym.lower()] = main_term


def transliterate_to_russian(text: str) -> str:
    """
    Транслитерация латиницы в кириллицу для технических терминов
    """
    translit_map = {
        'bort': 'борт',
        'truck': 'борт',
        'vehicle': 'техника',
        'dispatcher': 'диспетчер',
        'dispatch': 'диспетчер',
        'road': 'дорога',
        'schema': 'схема',
        'place': 'место',
        'tag': 'метка',
        'node': 'узел',
        'trip': 'рейс',
        'cargo': 'груз',
        'load': 'погрузка',
        'unload': 'разгрузка',
        'task': 'задание',
        'shift': 'смена',
        'status': 'статус',
        'user': 'пользователь',
        'role': 'роль',
        'auth': 'авторизация',
        'settings': 'настройка',
        'monitoring': 'мониторинг',
        'telemetry': 'телеметрия',
        'gps': 'координаты',
        'speed': 'скорость',
        'weight': 'вес',
        'fuel': 'топливо',
        'repair': 'ремонт',
        'idle': 'простой',
        'level': 'уровень',
        'edge': 'ребро',
        'ladder': 'лестница',
        'report': 'отчёт',
        'admin': 'администратор',
        'button': 'кнопка',
        'form': 'форма',
        'table': 'таблица',
        'map': 'карта',
        'chart': 'график',
        'filter': 'фильтр',
        'sort': 'сортировка',
        'export': 'экспорт',
        'import': 'импорт',
        'sync': 'синхронизация',
        'connection': 'подключение',
        'error': 'ошибка',
        'warning': 'предупреждение',
        'notification': 'уведомление',
        'logs': 'логи',
        'database': 'база данных',
        'service': 'сервис',
        'api': 'API',
        'request': 'запрос',
        'response': 'ответ',
        'token': 'токен',
        'session': 'сессия',
        'cache': 'кэш',
        'queue': 'очередь',
        'event': 'событие',
        'state': 'состояние',
        'transaction': 'транзакция',
        'migration': 'миграция',
        'container': 'контейнер',
        'deployment': 'развёртывание',
        'config': 'конфигурация'
    }
    
    text_lower = text.lower()
    for eng, rus in translit_map.items():
        # Заменяем целые слова (с границами слов)
        text_lower = re.sub(rf'\b{eng}\b', rus, text_lower)
    
    return text_lower


def fix_typos(text: str) -> str:
    """
    Исправление частых опечаток и неправильных символов
    """
    # Замена цифр на буквы (Борт0кортроль → борт контроль)
    text = re.sub(r'0', 'о', text)  # 0 → о
    text = re.sub(r'3', 'з', text)  # 3 → з
    text = re.sub(r'4', 'ч', text)  # 4 → ч
    text = re.sub(r'6', 'б', text)  # 6 → б
    text = re.sub(r'9', 'д', text)  # 9 → д
    
    # Удаление лишних символов
    text = re.sub(r'[-_/\\]', ' ', text)  # дефисы, подчёркивания, слэши → пробелы
    text = re.sub(r'\s+', ' ', text)  # множественные пробелы → один пробел
    
    return text.strip()


def expand_with_synonyms(text: str, max_synonyms: int = 3) -> str:
    """
    Расширение запроса синонимами
    
    Args:
        text: Исходный текст запроса
        max_synonyms: Максимальное количество синонимов на термин
    
    Returns:
        Расширенный текст с синонимами
    """
    words = text.lower().split()
    expanded_words: Set[str] = set()
    
    for word in words:
        # Добавляем само слово
        expanded_words.add(word)
        
        # Ищем основной термин для этого слова
        main_term = REVERSE_SYNONYMS.get(word)
        
        if main_term:
            # Добавляем основной термин
            expanded_words.add(main_term)
            
            # Добавляем топ-N синонимов
            synonyms = SYNONYMS.get(main_term, [])
            for synonym in synonyms[:max_synonyms]:
                expanded_words.add(synonym.lower())
    
    return ' '.join(expanded_words)


def normalize_query(query: str, expand_synonyms: bool = True) -> str:
    """
    Полная нормализация запроса
    
    Args:
        query: Исходный запрос пользователя
        expand_synonyms: Расширять ли запрос синонимами
    
    Returns:
        Нормализованный запрос
    
    Примеры:
        >>> normalize_query("bort-control")
        "борт контроль самосвал truck vehicle техника"
        
        >>> normalize_query("Борт0кортроль")
        "борт контроль самосвал truck vehicle техника"
        
        >>> normalize_query("как добавить метку?")
        "как добавить метка место точка узел"
    """
    # 1. Lowercase
    query = query.lower()
    
    # 2. Транслитерация (bort → борт)
    query = transliterate_to_russian(query)
    
    # 3. Исправление опечаток (Борт0кортроль → борт контроль)
    query = fix_typos(query)
    
    # 4. Расширение синонимами (опционально)
    if expand_synonyms:
        query = expand_with_synonyms(query, max_synonyms=3)
    
    return query


def extract_keywords(query: str) -> List[str]:
    """
    Извлечение ключевых слов из запроса (без стоп-слов)
    
    Args:
        query: Запрос пользователя
    
    Returns:
        Список ключевых слов
    """
    # Стоп-слова (частые слова без смысловой нагрузки)
    stop_words = {
        'как', 'что', 'где', 'когда', 'почему', 'зачем', 'кто', 'какой', 'какая', 'какие',
        'это', 'то', 'тот', 'эта', 'эти', 'в', 'на', 'с', 'по', 'для', 'из', 'к', 'у',
        'и', 'или', 'но', 'а', 'да', 'нет', 'не', 'ни', 'же', 'ли', 'бы', 'был', 'была',
        'я', 'ты', 'он', 'она', 'мы', 'вы', 'они', 'мой', 'твой', 'его', 'её', 'наш', 'ваш',
        'можно', 'нужно', 'надо', 'должен', 'может', 'мочь', 'хотеть', 'делать', 'сделать'
    }
    
    # Нормализуем запрос
    normalized = normalize_query(query, expand_synonyms=False)
    
    # Разбиваем на слова
    words = normalized.split()
    
    # Фильтруем стоп-слова и короткие слова
    keywords = [
        word for word in words 
        if word not in stop_words and len(word) > 2
    ]
    
    return keywords


if __name__ == "__main__":
    # Тесты
    test_queries = [
        "bort-control",
        "Борт0кортроль",
        "как добавить метку?",
        "схема дорог карьера",
        "создать наряд-задание",
        "truck status",
        "GPS координаты борта"
    ]
    
    print("=== ТЕСТЫ НОРМАЛИЗАЦИИ ЗАПРОСОВ ===\n")
    
    for query in test_queries:
        normalized = normalize_query(query)
        keywords = extract_keywords(query)
        
        print(f"Исходный:      {query}")
        print(f"Нормализован:  {normalized}")
        print(f"Ключевые слова: {', '.join(keywords)}")
        print()
