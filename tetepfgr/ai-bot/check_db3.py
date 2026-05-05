#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import chromadb

client = chromadb.PersistentClient(path='/app/chroma_data')
collection = client.get_collection('pgr_docs')

# Получаем все документы
results = collection.get(limit=300)

# Ищем чанки с текстом "Выбор смены" и "Откройте «Оперативная работа» → «Наряд-задание»"
found = []
for i, doc in enumerate(results['documents']):
    metadata = results['metadatas'][i] if results['metadatas'] else {}
    if ('Выбор смены' in doc and 'Наряд-задание' in doc) or 'Откройте «Оперативная работа» → «Наряд-задание»' in doc:
        found.append((i, doc, metadata))

print(f"Найдено чанков с инструкцией по созданию наряд-задания: {len(found)}")

for i, (idx, doc, meta) in enumerate(found):
    print(f"\n{'='*80}")
    print(f"Чанк #{i+1} (индекс {idx})")
    print(f"Файл: {meta.get('file', 'unknown')}")
    print(f"Секция: {meta.get('section', 'unknown')[:100]}")
    print(f"{'='*80}")
    print(doc)
    print(f"\n{'='*80}")
