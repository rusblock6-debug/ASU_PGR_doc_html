#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import chromadb

client = chromadb.PersistentClient(path='/app/chroma_data')
collection = client.get_collection('pgr_docs')

# Получаем все документы
results = collection.get(limit=300)

print(f"Всего чанков в базе: {len(results['documents'])}")

# Ищем чанки из файла "Данные из джейсона.md"
from_file = []
for i, doc in enumerate(results['documents']):
    metadata = results['metadatas'][i] if results['metadatas'] else {}
    if 'Данные из джейсона.md' in metadata.get('file', ''):
        from_file.append((i, doc, metadata))

print(f"\nЧанков из 'Данные из джейсона.md': {len(from_file)}")

# Показываем первые 10 чанков из этого файла
for i, (idx, doc, meta) in enumerate(from_file[:10]):
    print(f"\n{'='*60}")
    print(f"Чанк #{i+1} (индекс {idx})")
    print(f"Секция: {meta.get('section', 'unknown')[:80]}")
    print(f"{'='*60}")
    print(doc[:400])
    if len(doc) > 400:
        print("...")
