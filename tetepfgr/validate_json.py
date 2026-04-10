import json
import sys

try:
    with open('data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("✅ JSON валиден")
    print(f"Quickstart steps: {len(data['cards']['quickstart']['steps'])}")
    print(f"Descriptive sections: {len(data['cards']['descriptive'])}")
    print(f"Instructions: {len(data['cards']['instructions'])}")
    
    # Проверим что новый раздел добавлен
    bort_handbook = [s for s in data['cards']['descriptive'] if 'bort' in s.get('id', '').lower() or 'бортов' in s.get('title', '').lower()]
    bort_instructions = [i for i in data['cards']['instructions'] if 'bort' in i.get('id', '').lower() or 'бортов' in i.get('title', '').lower()]
    
    print(f"\n✅ Бортовой терминал handbook: {len(bort_handbook)} раздел(ов)")
    print(f"✅ Бортовой терминал instructions: {len(bort_instructions)} инструкций")
    
    if bort_handbook:
        print(f"   - Заголовок: {bort_handbook[0]['title']}")
        print(f"   - Шагов: {len(bort_handbook[0].get('steps', []))}")
    
    for inst in bort_instructions:
        print(f"   - {inst['title']}: {len(inst.get('steps', []))} шагов")
        
except Exception as e:
    print(f"❌ Ошибка: {e}")
    sys.exit(1)
