"""
Гибридный поиск: векторный + keyword + синонимы
"""
import logging
from typing import List, Dict, Any, Set
from .query_normalizer import normalize_query, extract_keywords

logger = logging.getLogger(__name__)


def remove_duplicates(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Удаление дубликатов из результатов поиска
    
    Args:
        results: Список результатов с полями 'id', 'document', 'metadata', 'distance'
    
    Returns:
        Список уникальных результатов
    """
    seen_ids: Set[str] = set()
    unique_results = []
    
    for result in results:
        result_id = result.get('id')
        if result_id and result_id not in seen_ids:
            seen_ids.add(result_id)
            unique_results.append(result)
    
    return unique_results


def merge_results(
    vector_results: Dict[str, Any],
    keyword_results: Dict[str, Any],
    vector_weight: float = 0.7,
    keyword_weight: float = 0.3
) -> List[Dict[str, Any]]:
    """
    Объединение результатов векторного и keyword поиска с весами
    
    Args:
        vector_results: Результаты векторного поиска из ChromaDB
        keyword_results: Результаты keyword поиска из ChromaDB
        vector_weight: Вес векторного поиска (0.0-1.0)
        keyword_weight: Вес keyword поиска (0.0-1.0)
    
    Returns:
        Объединённый список результатов с пересчитанными score
    """
    merged = []
    
    # Обрабатываем векторные результаты
    if vector_results.get('documents') and vector_results['documents'][0]:
        for i, doc in enumerate(vector_results['documents'][0]):
            distance = vector_results['distances'][0][i] if vector_results.get('distances') else 1.0
            # Cosine similarity: 1 - distance (distance ranges from 0 to 2 for cosine)
            # Convert to 0-1 range: max(0, 1 - distance/2)
            similarity = max(0.0, 1.0 - distance / 2.0)
            merged.append({
                'id': vector_results['ids'][0][i] if vector_results.get('ids') else f"vec_{i}",
                'document': doc,
                'metadata': vector_results['metadatas'][0][i] if vector_results.get('metadatas') else {},
                'distance': distance,
                'score': similarity * vector_weight,
                'source': 'vector'
            })
    
    # Обрабатываем keyword результаты
    if keyword_results.get('documents') and keyword_results['documents'][0]:
        for i, doc in enumerate(keyword_results['documents'][0]):
            distance = keyword_results['distances'][0][i] if keyword_results.get('distances') else 1.0
            # Cosine similarity: convert to 0-1 range
            similarity = max(0.0, 1.0 - distance / 2.0)
            merged.append({
                'id': keyword_results['ids'][0][i] if keyword_results.get('ids') else f"kw_{i}",
                'document': doc,
                'metadata': keyword_results['metadatas'][0][i] if keyword_results.get('metadatas') else {},
                'distance': distance,
                'score': similarity * keyword_weight,
                'source': 'keyword'
            })
    
    return merged


def rerank_results(
    results: List[Dict[str, Any]],
    original_query: str,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Переранжирование результатов по релевантности
    
    Args:
        results: Список результатов после объединения
        original_query: Исходный запрос пользователя
        top_k: Количество топ результатов для возврата
    
    Returns:
        Топ-K результатов после переранжирования
    """
    # Извлекаем ключевые слова из запроса
    keywords = set(extract_keywords(original_query))
    
    # Добавляем бонус за совпадение ключевых слов
    for result in results:
        doc_text = result['document'].lower()
        
        # Считаем количество совпадений ключевых слов
        keyword_matches = sum(1 for kw in keywords if kw in doc_text)
        
        # Добавляем бонус к score (до +0.3)
        keyword_bonus = min(keyword_matches * 0.1, 0.3)
        result['score'] += keyword_bonus
        
        # Бонус за тип источника (JSON документация важнее кода)
        if result['metadata'].get('source') == 'JSON':
            result['score'] += 0.2
        elif result['metadata'].get('type') == 'documentation':
            result['score'] += 0.15
    
    # Сортируем по score (от большего к меньшему)
    sorted_results = sorted(results, key=lambda x: x['score'], reverse=True)
    
    # Возвращаем топ-K
    return sorted_results[:top_k]


def hybrid_search(
    collection,
    question: str,
    n_results: int = 5,
    vector_n: int = 15,
    keyword_n: int = 10
) -> List[Dict[str, Any]]:
    """
    Гибридный поиск: векторный + keyword + синонимы
    
    Args:
        collection: ChromaDB коллекция
        question: Вопрос пользователя
        n_results: Количество финальных результатов
        vector_n: Количество результатов векторного поиска
        keyword_n: Количество результатов keyword поиска
    
    Returns:
        Список топ-N результатов после гибридного поиска
    
    Процесс:
        1. Нормализация запроса (транслитерация, опечатки, синонимы)
        2. Векторный поиск (semantic similarity)
        3. Keyword поиск (точные совпадения)
        4. Объединение результатов с весами
        5. Удаление дубликатов
        6. Переранжирование по релевантности
        7. Возврат топ-N
    """
    logger.info(f"🔍 Гибридный поиск: '{question}'")
    
    # 1. Нормализация запроса
    normalized_query = normalize_query(question, expand_synonyms=True)
    logger.info(f"📝 Нормализованный запрос: '{normalized_query}'")
    
    # 2. Векторный поиск (semantic)
    try:
        vector_results = collection.query(
            query_texts=[normalized_query],
            n_results=vector_n
        )
        logger.info(f"✅ Векторный поиск: найдено {len(vector_results.get('documents', [[]])[0])} результатов")
    except Exception as e:
        logger.error(f"❌ Ошибка векторного поиска: {e}")
        vector_results = {'documents': [[]], 'ids': [[]], 'metadatas': [[]], 'distances': [[]]}
    
    # 3. Keyword поиск (точные совпадения)
    keywords = extract_keywords(question)
    keyword_query = ' '.join(keywords)
    
    try:
        keyword_results = collection.query(
            query_texts=[keyword_query],
            n_results=keyword_n
        )
        logger.info(f"✅ Keyword поиск: найдено {len(keyword_results.get('documents', [[]])[0])} результатов")
    except Exception as e:
        logger.error(f"❌ Ошибка keyword поиска: {e}")
        keyword_results = {'documents': [[]], 'ids': [[]], 'metadatas': [[]], 'distances': [[]]}
    
    # 4. Объединение результатов
    merged = merge_results(vector_results, keyword_results)
    logger.info(f"🔗 Объединено: {len(merged)} результатов")
    
    # 5. Удаление дубликатов
    unique = remove_duplicates(merged)
    logger.info(f"🗑️ После дедупликации: {len(unique)} уникальных результатов")
    
    # 6. Переранжирование
    final_results = rerank_results(unique, question, top_k=n_results)
    logger.info(f"🏆 Финальные результаты: топ-{len(final_results)}")
    
    # Логируем топ-3 для отладки
    for i, result in enumerate(final_results[:3], 1):
        logger.info(f"  {i}. Score: {result['score']:.3f} | Source: {result['source']} | File: {result['metadata'].get('file', 'unknown')}")
    
    return final_results


if __name__ == "__main__":
    # Тесты (требуется ChromaDB коллекция)
    print("=== ТЕСТЫ ГИБРИДНОГО ПОИСКА ===\n")
    print("Для тестирования требуется подключение к ChromaDB")
    print("Запустите через main.py с реальной коллекцией")
