"""
Send indexing request directly to FastAPI using urllib.
No terminal needed - just run this script.
"""
import urllib.request
import json
import sys

print("=" * 60)
print("ЗАПУСК ПОЛНОЙ ИНДЕКСАЦИИ")
print("=" * 60)
print()

url = "http://localhost:8000/api/index?mode=full"
headers = {
    "X-API-Key": "change-me-in-production",
    "Content-Type": "application/json"
}

print(f"URL: {url}")
print(f"Method: POST")
print(f"Headers: {json.dumps(headers, indent=2)}")
print()
print("Запускаю индексацию...")
print("Это займет 5-15 минут. Не закрывайте окно!")
print("-" * 60)

try:
    req = urllib.request.Request(url, method='POST', headers=headers, data=b'{}')
    
    with urllib.request.urlopen(req, timeout=7200) as response:
        result = json.loads(response.read().decode())
        
        print()
        print("=" * 60)
        print("✅ ИНДЕКСАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        print("=" * 60)
        print()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
except urllib.error.HTTPError as e:
    print()
    print("=" * 60)
    print("❌ ОШИБКА HTTP")
    print("=" * 60)
    print(f"Status: {e.code}")
    print(f"Reason: {e.reason}")
    print(f"Body: {e.read().decode()}")
    sys.exit(1)
    
except Exception as e:
    print()
    print("=" * 60)
    print("❌ ОШИБКА")
    print("=" * 60)
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
