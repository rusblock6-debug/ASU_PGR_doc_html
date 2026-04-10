import json

with open('data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("=== ПРОВЕРКА СТРУКТУРЫ ===")
print(f"Quickstart steps: {len(data['cards']['quickstart']['steps'])}")
print(f"Descriptive sections: {len(data['cards']['descriptive'])}")
print(f"Instructions: {len(data['cards']['instructions'])}")

print("\n=== DESCRIPTIVE SECTIONS ===")
for s in data['cards']['descriptive']:
    print(f"  - {s['id']}: {s['title']}")

print("\n=== BORT TERMINAL SEARCH ===")
bort_in_desc = [s for s in data['cards']['descriptive'] if 'bort' in s.get('id','').lower() or 'бортов' in s.get('title','').lower()]
bort_in_instr = [s for s in data['cards']['instructions'] if 'bort' in s.get('id','').lower() or 'бортов' in s.get('title','').lower()]

print(f"\nВ descriptive: {len(bort_in_desc)} разделов")
for s in bort_in_desc:
    print(f"  - {s['id']}: {s['title']}")

print(f"\nВ instructions: {len(bort_in_instr)} разделов")
for s in bort_in_instr:
    print(f"  - {s['id']}: {s['title']} ({len(s.get('steps', []))} шагов)")
