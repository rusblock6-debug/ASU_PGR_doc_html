#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import chromadb

client = chromadb.PersistentClient(path='/app/chroma_data')
collection = client.get_collection('pgr_docs')

# Тестовый поиск
query = 'как взять задание для борта'
results = collection.query(query_texts=[query], n_results=5)

print(f'=== Поиск по запросу: "{query}" ===\n')
print(f'Найдено документов: {len(results["documents"][0])}\n')

for i, (doc, meta, distance) in enumerate(zip(
    results['documents'][0], 
    results['metadatas'][0],
    results['distances'][0]
)):
    print(f'--- Документ {i+1} ---')
    print(f'Файл: {meta.get("file", "unknown")}')
    print(f'Строка: {meta.get("line", "N/A")}')
    print(f'Дистанция: {distance:.4f}')
    print(f'Содержимое (первые 200 символов):')
    print(doc[:200])
    print()
