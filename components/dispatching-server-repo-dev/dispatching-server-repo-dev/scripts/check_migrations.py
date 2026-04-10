#!/usr/bin/env python3
"""
Скрипт проверки целостности миграций во всех сервисах.

Проверяет:
1. Формат имени файла: {revision}_{message}.py где revision - 3 цифры
2. Соответствие revision в файле имени файла
3. Последовательность миграций (без пропусков)
4. Корректность цепочки down_revision
5. Отсутствие дубликатов ревизий в рамках одного сервиса

Использование:
    python check_migrations.py
"""

import os
import re
import sys
from pathlib import Path
from dataclasses import dataclass


# Корневая директория проекта (относительно расположения скрипта)
SCRIPT_DIR = Path(__file__).parent
REPOS_DIR = SCRIPT_DIR.parent.parent / "repos"


@dataclass
class MigrationInfo:
    """Информация о миграции."""
    file_path: Path
    file_name: str
    file_revision: str | None  # Ревизия из имени файла
    code_revision: str | None  # Ревизия из кода (revision = '...')
    down_revision: str | None  # down_revision из кода


@dataclass
class ValidationError:
    """Ошибка валидации."""
    service: str
    file_name: str
    message: str
    severity: str  # 'error' или 'warning'


def find_services_with_migrations() -> list[tuple[str, Path]]:
    """Находит все сервисы с директорией migrations."""
    services = []

    if not REPOS_DIR.exists():
        print(f"Ошибка: директория repos не найдена: {REPOS_DIR}")
        return services

    for service_dir in REPOS_DIR.iterdir():
        if not service_dir.is_dir():
            continue

        # Проверяем стандартные пути до директории versions
        possible_paths = [
            service_dir / "migrations" / "versions",
            service_dir / "app" / "migrations" / "versions",
        ]

        for versions_path in possible_paths:
            if versions_path.exists() and versions_path.is_dir():
                services.append((service_dir.name, versions_path))
                break

    return services


def parse_migration_file(file_path: Path) -> MigrationInfo:
    """Парсит файл миграции и извлекает информацию о ревизиях."""
    file_name = file_path.name
    
    # Извлекаем ревизию из имени файла
    file_revision_match = re.match(r'^(\d{3})_', file_name)
    file_revision = file_revision_match.group(1) if file_revision_match else None
    
    code_revision = None
    down_revision = None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Ищем revision = '...' (только строки из 3 цифр или специальные форматы)
        rev_match = re.search(r"^revision\s*=\s*['\"](\d{3})['\"]", content, re.MULTILINE)
        if rev_match:
            code_revision = rev_match.group(1)
        else:
            # Попробуем найти любой формат revision
            rev_match_any = re.search(r"^revision\s*=\s*['\"]([^'\"]+)['\"]", content, re.MULTILINE)
            if rev_match_any:
                code_revision = rev_match_any.group(1)
        
        # Ищем down_revision = '...' или None
        down_match = re.search(r"^down_revision\s*=\s*['\"](\d{3})['\"]", content, re.MULTILINE)
        if down_match:
            down_revision = down_match.group(1)
        else:
            # Проверяем на None
            down_none_match = re.search(r"^down_revision\s*=\s*None", content, re.MULTILINE)
            if down_none_match:
                down_revision = None
            else:
                # Попробуем найти любой формат
                down_match_any = re.search(r"^down_revision\s*=\s*['\"]([^'\"]+)['\"]", content, re.MULTILINE)
                if down_match_any:
                    down_revision = down_match_any.group(1)
    except Exception as e:
        print(f"  Ошибка чтения файла {file_path}: {e}")
    
    return MigrationInfo(
        file_path=file_path,
        file_name=file_name,
        file_revision=file_revision,
        code_revision=code_revision,
        down_revision=down_revision
    )


def validate_service_migrations(service_name: str, versions_dir: Path) -> list[ValidationError]:
    """Проверяет миграции для одного сервиса."""
    errors = []
    migrations: list[MigrationInfo] = []
    
    # Собираем все миграции
    for file_path in sorted(versions_dir.iterdir()):
        if file_path.is_file() and file_path.suffix == '.py' and file_path.name != '__init__.py':
            migration = parse_migration_file(file_path)
            migrations.append(migration)
    
    if not migrations:
        return errors
    
    # Фильтруем только миграции с трехзначными ревизиями в имени файла
    numbered_migrations = [m for m in migrations if m.file_revision is not None]
    
    # Сортируем по номеру ревизии
    numbered_migrations.sort(key=lambda m: int(m.file_revision) if m.file_revision else 0)
    
    # Проверка 1: Формат имени файла
    for migration in migrations:
        if migration.file_revision is None:
            # Проверяем, не является ли это стандартным Alembic хешем
            if re.match(r'^[a-f0-9]+_', migration.file_name):
                errors.append(ValidationError(
                    service=service_name,
                    file_name=migration.file_name,
                    message="Файл использует стандартный Alembic формат (хеш). Нужно переименовать в формат '{NNN}_{message}.py'",
                    severity='warning'
                ))
            elif not migration.file_name.startswith('__'):
                errors.append(ValidationError(
                    service=service_name,
                    file_name=migration.file_name,
                    message="Имя файла не соответствует формату '{NNN}_{message}.py'",
                    severity='error'
                ))
    
    # Проверка 2: Соответствие ревизии в файле и имени файла
    # Ревизия в коде должна быть ровно 3 цифры и совпадать с именем файла
    for migration in numbered_migrations:
        if migration.code_revision and migration.file_revision:
            # Проверяем что revision в коде это ровно 3 цифры
            if not re.match(r'^\d{3}$', migration.code_revision):
                errors.append(ValidationError(
                    service=service_name,
                    file_name=migration.file_name,
                    message=f"revision в коде должен быть 3 цифры ('{migration.file_revision}'), но имеет '{migration.code_revision}'",
                    severity='error'
                ))
            elif migration.code_revision != migration.file_revision:
                errors.append(ValidationError(
                    service=service_name,
                    file_name=migration.file_name,
                    message=f"Ревизия в коде ('{migration.code_revision}') не соответствует имени файла ('{migration.file_revision}')",
                    severity='error'
                ))
    
    # Проверка 3: Дубликаты ревизий
    if numbered_migrations:
        revision_to_files: dict[str, list[str]] = {}
        for migration in numbered_migrations:
            if migration.file_revision:
                if migration.file_revision not in revision_to_files:
                    revision_to_files[migration.file_revision] = []
                revision_to_files[migration.file_revision].append(migration.file_name)
        
        for revision, files in revision_to_files.items():
            if len(files) > 1:
                errors.append(ValidationError(
                    service=service_name,
                    file_name="",
                    message=f"Дубликат ревизии '{revision}': {', '.join(files)}",
                    severity='error'
                ))
    
    # Проверка 4: Последовательность миграций (без пропусков)
    if numbered_migrations:
        # Используем уникальные номера для проверки последовательности
        revision_numbers = list(set(int(m.file_revision) for m in numbered_migrations if m.file_revision))
        revision_numbers.sort()
        
        for i in range(len(revision_numbers) - 1):
            if revision_numbers[i + 1] - revision_numbers[i] > 1:
                errors.append(ValidationError(
                    service=service_name,
                    file_name="",
                    message=f"Пропуск в последовательности: после {revision_numbers[i]:03d} идет {revision_numbers[i + 1]:03d}",
                    severity='error'
                ))
    
    # Проверка 5: Корректность цепочки down_revision
    # Первая миграция (минимальный номер) должна иметь down_revision = None
    # Остальные должны ссылаться на предыдущую
    if numbered_migrations:
        first_revision_num = min(int(m.file_revision) for m in numbered_migrations if m.file_revision)
        
        for migration in numbered_migrations:
            if migration.file_revision:
                current_num = int(migration.file_revision)
                
                if current_num == first_revision_num:
                    # Первая миграция должна иметь down_revision = None
                    if migration.down_revision is not None:
                        errors.append(ValidationError(
                            service=service_name,
                            file_name=migration.file_name,
                            message=f"Первая миграция ({migration.file_revision}) должна иметь down_revision = None, но имеет '{migration.down_revision}'",
                            severity='error'
                        ))
                else:
                    expected_down = f"{current_num - 1:03d}"
                    # down_revision тоже должен быть в формате 3 цифр
                    if migration.down_revision != expected_down:
                        errors.append(ValidationError(
                            service=service_name,
                            file_name=migration.file_name,
                            message=f"down_revision должен быть '{expected_down}', но имеет '{migration.down_revision}'",
                            severity='error'
                        ))
    
    return errors


def print_report(all_errors: dict[str, list[ValidationError]]) -> int:
    """Выводит отчет о проверке и возвращает код выхода."""
    total_errors = 0
    total_warnings = 0

    for service_name, errors in sorted(all_errors.items()):
        service_errors = [e for e in errors if e.severity == 'error']
        service_warnings = [e for e in errors if e.severity == 'warning']

        if not errors:
            print(f"[OK] {service_name}")
        else:
            status = "ISSUES"  # Общий статус для любых проблем
            print(f"[{status}] {service_name}")

            for error in errors:
                prefix = "  ERROR:" if error.severity == 'error' else "  WARNING:"
                file_info = f" ({error.file_name})" if error.file_name else ""
                print(f"{prefix}{file_info} {error.message}")

        total_errors += len(service_errors)
        total_warnings += len(service_warnings)

    print("")
    print(f"Итого: {total_errors} ошибок, {total_warnings} предупреждений")

    # Возвращаем 1 при любых несоответствиях (ошибки или предупреждения)
    return 1 if (total_errors > 0 or total_warnings > 0) else 0


def main():
    print("Проверка целостности миграций")
    print("=" * 50)
    print("")

    services = find_services_with_migrations()

    if not services:
        print("Сервисы с миграциями не найдены")
        sys.exit(0)

    print(f"Найдено сервисов с миграциями: {len(services)}")
    for service_name, versions_dir in services:
        print(f"  - {service_name}: {versions_dir}")
    print("")

    all_errors: dict[str, list[ValidationError]] = {}

    for service_name, versions_dir in services:
        errors = validate_service_migrations(service_name, versions_dir)
        all_errors[service_name] = errors

    print("Результаты проверки:")
    print("-" * 50)

    exit_code = print_report(all_errors)

    # Возвращаем exit code: 0 - все OK, 1 - есть проблемы
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

