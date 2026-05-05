# -*- coding: utf-8 -*-
import chromadb

client = chromadb.PersistentClient(path='tetepfgr/ai-bot/chroma_data')
collection = client.get_collection('pgr_docs')

# Получаем все документы
results = collection.get(limit=300)

print(f"Всего чанков в базе: {len(results['documents'])}")

# Ищем чанки с "Создание заданий"
found = []
for i, doc in enumerate(results['documents']):
    if 'Создание заданий' in doc or 'создание заданий' in doc.lower():
        found.append((i, doc))

print(f"\nНайдено чанков с 'Создание заданий': {len(found)}")

for i, (idx, doc) in enumerate(found[:3]):
    print(f"\n{'='*60}")
    print(f"Чанк #{i+1} (индекс {idx})")
    print(f"{'='*60}")
    print(doc[:800])
    print("...")
