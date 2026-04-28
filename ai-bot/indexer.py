"""
Модуль индексации файлов репозитория
"""
import os
import hashlib
from pathlib import Path
from typing import List, Dict, Set
import logging

logger = logging.getLogger(__name__)

# Чёрный список папок
EXCLUDED_DIRS = {
    '.git', 'node_modules', '__pycache__', 'logs',
    'chroma_data', 'ollama_data', 'redis_data',
    '.vscode', '.idea', 'dist', 'build', 'target',
    '.next', '.nuxt', 'coverage', '.pytest_cache',
    'screenshots', '.history', '.cursor', '.husky',
    '.storybook', 'migrations', 'tests', 'test',
    '.docker', '.bin', 'monitoring', 'telemetry-visualizer',
    'documentation'  # Временно исключено (docx/xlsx файлы)
}

# Чёрный список расширений
EXCLUDED_EXTENSIONS = {
    '.log', '.pyc', '.pyo', '.so', '.dll', '.exe',
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico',
    '.mp4', '.avi', '.mov', '.mp3', '.wav',
    '.zip', '.tar', '.gz', '.rar', '.7z',
    '.lock', '.sum', '.sqlite3', '.db', '.rdb',
    '.woff', '.woff2', '.ttf', '.eot', '.svg',
    '.min.js', '.min.css', '.map'
}

# Служебные файлы
EXCLUDED_FILES = {
    '.env', '.env.local', '.env.production', '.env.example',
    '.gitignore', '.dockerignore', '.eslintignore',
    'package-lock.json', 'yarn.lock', 'poetry.lock',
    'uv.lock', 'go.sum', 'Dockerfile', 'docker-compose.yml',
    'docker-compose.yaml', '.gitlab-ci.yml', '.pre-commit-config.yaml',
    'admin_git.html',  # Дубликат admin.html для веб-просмотра
    'QUICK_START_HYBRID.md',  # Временная документация
    'DEPLOYMENT_FIXES.md'  # Лог исправлений
}

# Максимальный размер файла (1MB)
MAX_FILE_SIZE = 1024 * 1024

class RepositoryScanner:
    """Сканер репозитория"""
    
    def __init__(self, repo_path: str = "/data/repo"):
        self.repo_path = Path(repo_path)
        
    def should_exclude(self, path: Path) -> bool:
        """Проверка, нужно ли исключить файл/папку"""
        # Проверка папок
        for part in path.parts:
            if part in EXCLUDED_DIRS:
                return True
        
        # Проверка расширений
        if path.suffix.lower() in EXCLUDED_EXTENSIONS:
            return True
        
        # Проверка имён файлов
        if path.name in EXCLUDED_FILES:
            return True
        
        return False
    
    def scan_files(self) -> List[Dict]:
        """Сканирование всех файлов репозитория"""
        files = []
        
        logger.info(f"Начало сканирования: {self.repo_path}")
        
        for root, dirs, filenames in os.walk(self.repo_path):
            # Исключаем папки из обхода
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
            
            for filename in filenames:
                file_path = Path(root) / filename
                
                if self.should_exclude(file_path):
                    continue
                
                try:
                    # Проверка размера файла
                    file_size = file_path.stat().st_size
                    if file_size > MAX_FILE_SIZE:
                        logger.debug(f"Файл слишком большой ({file_size} bytes): {file_path}")
                        continue
                    
                    # Вычисляем MD5
                    with open(file_path, 'rb') as f:
                        file_hash = hashlib.md5(f.read()).hexdigest()
                    
                    # Относительный путь
                    rel_path = file_path.relative_to(self.repo_path)
                    
                    files.append({
                        'path': str(rel_path),
                        'full_path': str(file_path),
                        'hash': file_hash,
                        'size': file_path.stat().st_size,
                        'extension': file_path.suffix
                    })
                    
                except Exception as e:
                    logger.warning(f"Ошибка чтения {file_path}: {e}")
        
        logger.info(f"Найдено файлов: {len(files)}")
        return files
    
    def get_changed_files(self, old_hashes: Dict[str, str]) -> tuple:
        """Определение изменённых файлов"""
        current_files = self.scan_files()
        current_hashes = {f['path']: f['hash'] for f in current_files}
        
        added = []
        modified = []
        deleted = []
        
        # Новые и изменённые
        for path, hash_val in current_hashes.items():
            if path not in old_hashes:
                added.append(path)
            elif old_hashes[path] != hash_val:
                modified.append(path)
        
        # Удалённые
        for path in old_hashes:
            if path not in current_hashes:
                deleted.append(path)
        
        return added, modified, deleted
