import re
from typing import Dict, List, Set


def extract_common_variables(template_file_path: str = ".env_bort_template") -> dict:
    """Извлекает переменные из шаблона, включая все три секции"""
    with open(template_file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')

    common_vars = {}
    specific_vars = []
    vehicle_dependant_vars = {}
    current_section = None
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Определение секций по заголовкам
        if '# Matching Variables' in line or 'MATCHING VARIABLES' in line.upper():
            current_section = 'common'
        elif '# Different Variables' in line or 'DIFFERENT VARIABLES' in line.upper():
            current_section = 'specific'
        elif '# VEHICLE-DEPENDANT VARIABLES' in line or 'VEHICLE-DEPENDANT VARIABLES' in line.upper():
            current_section = 'vehicle_dependant'

        elif line.startswith('#') or not line:
            i += 1
            continue

        # Обработка секции MATCHING VARIABLES (фиксированные значения)
        elif current_section == 'common' and '=' in line:
            key, value = line.split('=', 1)
            common_vars[key.strip()] = value.strip()

        # Обработка секции DIFFERENT VARIABLES (переменные без значений)
        elif current_section == 'specific':
            # Извлекаем имя переменной (до комментария, если он есть)
            var_name = line.split('#')[0].strip()
            if var_name:  # Добавляем только непустые имена
                specific_vars.append(var_name)

        # Обработка секции VEHICLE-DEPENDANT VARIABLES (шаблоны с {VEHICLE_ID})
        elif current_section == 'vehicle_dependant' and '=' in line:
            key, value = line.split('=', 1)
            vehicle_dependant_vars[key.strip()] = value.strip()

        i += 1

    return {
        'common': common_vars,
        'specific': specific_vars,
        'vehicle_dependant': vehicle_dependant_vars
    }
