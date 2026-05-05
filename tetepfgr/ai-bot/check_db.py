#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import chromadb

client = chromadb.PersistentClient(path='/app/chroma_data')
collection = client.get_collection('pgr_docs')

# Получаем все документы
results = collection.get(limit=300)

print(f"Всего чанков в базе: {len(results['documents'])}")

# Ищем чанки с "Создание заданий"
found = []
for i, doc in enumerate(results['documents']):
    if 'Создание заданий' in doc or 'создание заданий' in doc.lower():
        metadata = results['metadatas'][i] if results['metadatas'] else {}
        found.append((i, doc, metadata))

print(f"\nНайдено чанков с 'Создание заданий': {len(found)}")

for i, (idx, doc, meta) in enumerate(found[:3]):
    print(f"\n{'='*60}")
    print(f"Чанк #{i+1} (индекс {idx})")
    print(f"Файл: {meta.get('file', 'unknown')}")
    print(f"Секция: {meta.get('section', 'unknown')}")
    print(f"{'='*60}")
    print(doc[:800])
    if len(doc) > 800:
        print("...")
