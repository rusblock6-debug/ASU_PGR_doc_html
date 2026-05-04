#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import chromadb

client = chromadb.PersistentClient(path='/app/chroma_data')
collection = client.get_collection('pgr_docs')

# Получаем все чанки из файла
results = collection.get(
    where={"file": "Данные из джейсона.md"},
    limit=1000
)

print(f'Всего чанков: {len(results["documents"])}\n')

# Ищем чанки вокруг строк 50-70
print('=== Чанки вокруг строк 50-70 ===\n')
for doc, meta in zip(results['documents'], results['metadatas']):
    line = meta.get('line', 0)
    if 45 <= line <= 75:
        print(f'--- Строка {line} ---')
        print(f'Тип: {meta.get("type", "unknown")}')
        print(f'Содержимое:')
        print(doc)
        print('\n')
