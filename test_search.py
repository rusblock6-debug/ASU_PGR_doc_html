#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import json

# Тестируем поиск
response = requests.post(
    'http://localhost:8000/api/ask',
    headers={'X-API-Key': 'change-me-in-production'},
    json={'question': 'Как создать наряд-задание?'},
    timeout=300
)

result = response.json()

print("="*80)
print("ОТВЕТ БОТА:")
print("="*80)
print(result.get('answer', 'Нет ответа'))
print("\n" + "="*80)
print("ИСТОЧНИКИ:")
print("="*80)
for i, source in enumerate(result.get('sources', []), 1):
    print(f"{i}. {source.get('file', 'unknown')} (score: {source.get('score', 0)})")
print("\n" + "="*80)
print(f"Время ответа: {result.get('response_time', 0):.1f}с")
print("="*80)
