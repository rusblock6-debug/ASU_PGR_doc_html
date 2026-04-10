#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для конвертации данные.txt в data.json формат
"""

import json
import re

def parse_txt_to_json(txt_file):
    """Парсит данные.txt и создает структуру для data.json"""
    
    with open(txt_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Разделяем на секции по номерам разделов верхнего уровня
    sections = re.split(r'\n(?=\d+\.\s[А-Я])', content)
    
    result = {
        "title": "Инструкция пользователя АСУ ПГР",
        "cards": {
            "quickstart": None,
            "descriptive": [],
            "instructions": [],
            "about": []
        }
    }
    
    for section in sections:
        if not section.strip():
            continue
            
        # Определяем тип раздела
        if '1. Введение' in section or '7. Быстрый старт' in section:
            # Это quickstart - уже создан вручную
            pass
        elif '15. Общие разделы' in section:
            # Это descriptive - обзор главных окон
            result['cards']['descriptive'] = parse_descriptive(section)
        elif '16. Инструкции' in section:
            # Это инструкции
            result['cards']['instructions'] = parse_instructions_section(section)
        elif re.match(r'^\d+\.\s', section):
            # Остальные разделы добавляем как инструкции
            instr = parse_single_instruction(section)
            if instr:
                result['cards']['instructions'].append(instr)
    
    # Добавляем about
    result['cards']['about'] = [{
        "id": "about-guide",
        "title": "О руководстве",
        "navTitle": "О руководстве",
        "content": "<div class='instruction-content'><p>Полное руководство пользователя АСУ ПГР.</p></div>"
    }]
    
    return result

def parse_descriptive(text):
    """Парсит раздел с описанием главных окон"""
    cards = []
    
    if 'Справочники (общее описание)' in text:
        cards.append({
            "id": "handbooks",
            "title": "Справочники",
            "subtitle": "Настройка цифровой модели рудника",
            "description": "Основной раздел для настройки цифровой модели рудника.",
            "items": [
                "Модели техники и единицы оборудования",
                "Статусы для классификации времени",
                "Виды груза с параметрами плотности",
                "Горизонты (уровни рудника)",
                "Места погрузки и разгрузки",
                "Метки позиционирования",
                "Производственные участки"
            ],
            "image": "screenshots/main-windows/handbooks.png"
        })
    
    if 'Оперативная работа (общее описание)' in text:
        cards.append({
            "id": "operational",
            "title": "Оперативная работа",
            "subtitle": "Ежедневное планирование и мониторинг",
            "description": "Раздел для ежедневного планирования и мониторинга.",
            "items": [
                "Наряд-задания — создание сменных заданий",
                "Управление рейсами — просмотр рейсов",
                "Карта рабочего времени (КРВ)",
                "Карта рудника — 2D/3D отображение"
            ],
            "image": "screenshots/main-windows/operational.png"
        })
    
    if 'Аналитика (общее описание)' in text:
        cards.append({
            "id": "analytics",
            "title": "Аналитика",
            "subtitle": "Анализ производительности",
            "description": "Раздел для анализа производительности.",
            "items": [
                "Сводка по маршрутам",
                "По видам груза",
                "Эффективность техники"
            ],
            "image": "screenshots/main-windows/analytics.png"
        })
    
    if 'Навигация по системе' in text:
        cards.append({
            "id": "navigation",
            "title": "Навигация по системе",
            "subtitle": "Интерфейс и управление",
            "description": "Общее описание интерфейса системы.",
            "items": [
                "Верхняя панель — меню навигации",
                "Левая боковая панель — фильтры и списки",
                "Основная рабочая область — таблицы и графики"
            ],
            "image": "screenshots/main-windows/navigation.png"
        })
    
    return cards

def parse_instructions_section(text):
    """Парсит раздел 16 с пошаговыми инструкциями"""
    instructions = []
    
    # Парсим каждую подсекцию
    if 'Как настроить систему с нуля?' in text:
        instructions.append({
            "id": "setup_system",
            "title": "Как настроить систему с нуля?",
            "navTitle": "Настройка системы",
            "description": "Пошаговая настройка всех компонентов системы",
            "items": [
                "Создание моделей техники",
                "Добавление единиц техники",
                "Настройка статусов",
                "Создание видов груза",
                "Настройка горизонтов",
                "Создание мест работ",
                "Настройка меток позиционирования"
            ],
            "steps": [
                {
                    "text": "Шаг 1: Создание моделей техники",
                    "images": [
                        "screenshots/instructions/create_model_1.png",
                        "screenshots/instructions/create_model_2.png"
                    ],
                    "horizontal": True
                },
                {
                    "text": "Шаг 2: Добавление единиц техники",
                    "images": [
                        "screenshots/instructions/add_vehicle_1.png",
                        "screenshots/instructions/add_vehicle_2.png"
                    ],
                    "horizontal": True
                },
                {
                    "text": "Шаг 3: Настройка статусов",
                    "images": ["screenshots/instructions/setup_statuses.png"],
                    "horizontal": False
                },
                {
                    "text": "Шаг 4: Создание видов груза",
                    "images": ["screenshots/instructions/create_cargo.png"],
                    "horizontal": False
                },
                {
                    "text": "Шаг 5: Настройка горизонтов",
                    "images": ["screenshots/instructions/create_horizons.png"],
                    "horizontal": False
                },
                {
                    "text": "Шаг 6: Создание мест работ",
                    "images": [
                        "screenshots/instructions/create_places_1.png",
                        "screenshots/instructions/create_places_2.png"
                    ],
                    "horizontal": True
                },
                {
                    "text": "Шаг 7: Настройка меток позиционирования",
                    "images": ["screenshots/instructions/setup_tags.png"],
                    "horizontal": False
                }
            ],
            "keyIndicators": [
                "Все справочники настроены",
                "Техника добавлена в систему",
                "Система готова к работе"
            ]
        })
    
    if 'Как создать наряд-задание на смену?' in text:
        instructions.append({
            "id": "create_work_order",
            "title": "Как создать наряд-задание на смену?",
            "navTitle": "Создание наряд-заданий",
            "description": "Планирование сменных заданий",
            "items": [
                "Выбор смены",
                "Создание маршрутного задания",
                "Активация задания",
                "Мониторинг выполнения"
            ],
            "steps": [
                {
                    "text": "Шаг 1: Выбор смены",
                    "images": ["screenshots/instructions/select_shift.png"],
                    "horizontal": False
                },
                {
                    "text": "Шаг 2: Создание маршрутного задания",
                    "images": [
                        "screenshots/instructions/create_work_order_1.png",
                        "screenshots/instructions/create_work_order_2.png"
                    ],
                    "horizontal": True
                },
                {
                    "text": "Шаг 3: Активация задания",
                    "images": ["screenshots/instructions/activate_task.png"],
                    "horizontal": False
                },
                {
                    "text": "Шаг 4: Мониторинг выполнения",
                    "images": ["screenshots/instructions/monitor_execution.png"],
                    "horizontal": False
                }
            ],
            "keyIndicators": [
                "Наряд-задание создано",
                "Задание активировано",
                "Рейсы выполняются"
            ]
        })
    
    if 'Как работать с картой рабочего времени?' in text:
        instructions.append({
            "id": "work_with_krv",
            "title": "Как работать с картой рабочего времени?",
            "navTitle": "Карта рабочего времени",
            "description": "Визуализация и анализ использования времени",
            "items": [
                "Открытие КРВ",
                "Добавление статуса",
                "Редактирование статуса",
                "Анализ эффективности"
            ],
            "steps": [
                {
                    "text": "Шаг 1: Открытие КРВ",
                    "images": ["screenshots/instructions/open_krv.png"],
                    "horizontal": False
                },
                {
                    "text": "Шаг 2: Добавление статуса",
                    "images": [
                        "screenshots/instructions/add_status_krv_1.png",
                        "screenshots/instructions/add_status_krv_2.png"
                    ],
                    "horizontal": True
                },
                {
                    "text": "Шаг 3: Редактирование статуса",
                    "images": ["screenshots/instructions/edit_status_krv.png"],
                    "horizontal": False
                },
                {
                    "text": "Шаг 4: Анализ эффективности",
                    "images": ["screenshots/instructions/analyze_krv.png"],
                    "horizontal": False
                }
            ],
            "keyIndicators": [
                "КИОВ рассчитан",
                "Все статусы отражены",
                "Эффективность оценена"
            ]
        })
    
    if 'Как анализировать результаты работы?' in text:
        instructions.append({
            "id": "analyze_results",
            "title": "Как анализировать результаты работы?",
            "navTitle": "Анализ результатов",
            "description": "Просмотр отчетов и аналитики",
            "items": [
                "Сводка по маршрутам",
                "Анализ по видам груза",
                "Оценка эффективности",
                "Экспорт отчетов"
            ],
            "steps": [
                {
                    "text": "Шаг 1: Просмотр сводки по маршрутам",
                    "images": ["screenshots/instructions/route_summary.png"],
                    "horizontal": False
                },
                {
                    "text": "Шаг 2: Анализ по видам груза",
                    "images": ["screenshots/instructions/cargo_analysis.png"],
                    "horizontal": False
                },
                {
                    "text": "Шаг 3: Оценка эффективности техники",
                    "images": ["screenshots/instructions/efficiency_analysis.png"],
                    "horizontal": False
                },
                {
                    "text": "Шаг 4: Экспорт отчетов",
                    "images": ["screenshots/instructions/export_reports.png"],
                    "horizontal": False
                }
            ],
            "keyIndicators": [
                "Отчеты сформированы",
                "Показатели проанализированы",
                "Выявлены области улучшения"
            ]
        })
    
    return instructions

def parse_single_instruction(text):
    """Парсит один раздел как инструкцию"""
    # Извлекаем заголовок
    match = re.match(r'^(\d+)\.\s+(.+)', text)
    if not match:
        return None
    
    num, title = match.groups()
    
    # Извлекаем все скриншоты
    screenshots = re.findall(r'https://screenshots/(.+\.png)', text)
    
    # Создаем простую инструкцию
    return {
        "id": f"section_{num}",
        "title": title,
        "navTitle": title,
        "description": f"Раздел {num}: {title}",
        "items": ["Смотрите подробную документацию"],
        "steps": [
            {
                "text": "Подробная инструкция",
                "images": [f"screenshots/{s}" for s in screenshots[:5]],  # Берем первые 5
                "horizontal": False
            }
        ],
        "keyIndicators": []
    }

if __name__ == '__main__':
    import sys
    
    txt_file = 'данные.txt'
    output_file = 'data_full.json'
    
    print("Парсинг данные.txt...")
    data = parse_txt_to_json(txt_file)
    
    print(f"Создано {len(data['cards']['instructions'])} инструкций")
    print(f"Создано {len(data['cards']['descriptive'])} описаний")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Результат сохранен в {output_file}")
