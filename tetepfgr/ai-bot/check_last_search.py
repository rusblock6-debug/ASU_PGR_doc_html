#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import chromadb
from src.hybrid_search import hybrid_search

client = chromadb.PersistentClient(path='/app/chroma_data')
collection = client.get_collection('pgr_docs')

# Выполняем тот же поиск что и бот
question = "Как создать наряд-задание?"
results = hybrid_search(
    collection=collection,
    question=question,
    n_results=10,
    vector_n=50,
    keyword_n=30
)

print(f"Найдено результатов: {len(results)}\n")

for i, result in enumerate(results[:5], 1):
    print(f"{'='*80}")
    print(f"Результат #{i}")
    print(f"Score: {result['score']:.3f}")
    print(f"Source: {result['source']}")
    print(f"File: {result['metadata'].get('file', 'unknown')}")
    print(f"Section: {result['metadata'].get('section', 'unknown')[:100]}")
    print(f"{'='*80}")
    print(result['document'][:800])
    if len(result['document']) > 800:
        print("...")
    print()
