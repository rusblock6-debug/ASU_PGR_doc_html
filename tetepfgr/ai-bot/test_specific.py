#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import chromadb

client = chromadb.PersistentClient(path='/app/chroma_data')
collection = client.get_collection('pgr_docs')

# Ищем конкретный текст про создание маршрута
results = collection.get(
    where={"file": "Данные из джейсона.md"},
    limit=1000
)

print(f'Всего чанков из файла "Данные из джейсона.md": {len(results["documents"])}\n')

# Ищем чанки со строками 55-70
target_chunks = []
for doc, meta in zip(results['documents'], results['metadatas']):
    line = meta.get('line', 0)
    if 55 <= line <= 70:
        target_chunks.append((line, doc[:300]))

print('=== Чанки со строками 55-70 (про создание маршрута) ===\n')
for line, content in sorted(target_chunks):
    print(f'Строка {line}:')
    print(content)
    print('---\n')

# Теперь проверим поиск
print('\n=== Тестовый поиск ===\n')
queries = [
    'как взять задание для борта',
    'создание маршрута для техники',
    'наряд-задание создать маршрут',
    'отправить задание борту'
]

for query in queries:
    results = collection.query(query_texts=[query], n_results=3)
    print(f'Запрос: "{query}"')
    for i, (meta, dist) in enumerate(zip(results['metadatas'][0], results['distances'][0])):
        print(f'  {i+1}. {meta.get("file")} строка {meta.get("line")} (дистанция: {dist:.3f})')
    print()
