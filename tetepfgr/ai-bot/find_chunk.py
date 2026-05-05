#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import chromadb

client = chromadb.PersistentClient(path='/app/chroma_data')
collection = client.get_collection('pgr_docs')

# Получаем все документы
results = collection.get(limit=300)

# Ищем чанк с "Создание маршрута"
found = []
for i, doc in enumerate(results['documents']):
    if 'Создание маршрута' in doc or 'создание маршрута' in doc.lower():
        metadata = results['metadatas'][i] if results['metadatas'] else {}
        found.append((i, doc, metadata))

print(f"Найдено чанков с 'Создание маршрута': {len(found)}\n")

for i, (idx, doc, meta) in enumerate(found[:3]):
    print(f"{'='*80}")
    print(f"Чанк #{i+1} (индекс {idx})")
    print(f"Файл: {meta.get('file', 'unknown')}")
    print(f"{'='*80}")
    print(doc)
    print()
