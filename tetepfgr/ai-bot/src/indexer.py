"""
Модуль индексации файлов репозитория
"""
import os
import hashlib
from pathlib import Path
from typing import List, Dict, Set
import logging

logger = logging.getLogger(__name__)

# Парсер документации отключен - знания извлекаются из кода напрямую
PARSER_AVAILABLE = False

# Чёрный список папок
EXCLUDED_DIRS = {
    '.git', 'node_modules', '__pycache__', 'logs',
    'chroma_data', 'ollama_data', 'redis_data',
    '.vscode', '.idea', 'dist', 'build', 'target',
    '.next', '.nuxt', 'coverage', '.pytest_cache',
    'screenshots', '.history', '.cursor', '.husky',
    '.storybook', 'migrations', 'tests', 'test',
    '.docker', '.bin', 'monitoring', 'telemetry-visualizer',
    'library'  # JavaScript библиотеки (pdf-lib, html2pdf и т.д.)
}

# Чёрный список расширений
EXCLUDED_EXTENSIONS = {
    '.log', '.pyc', '.pyo', '.so', '.dll', '.exe',
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico',
    '.mp4', '.avi', '.mov', '.mp3', '.wav',
    '.zip', '.tar', '.gz', '.rar', '.7z',
    '.lock', '.sum', '.sqlite3', '.db', '.rdb',
    '.woff', '.woff2', '.ttf', '.eot', '.svg',
    '.min.js', '.min.css', '.map',
    '.bundle.js', '.bundle.css'  # Бандлы (webpack, rollup и т.д.)
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
    'DEPLOYMENT_FIXES.md',  # Лог исправлений
    'chat.js', 'chat.css', 'server.js',  # Frontend файлы tetepfgr
    'admin.html'  # HTML интерфейс (не нужен для RAG)
}

# Максимальный размер файла (1MB)
MAX_FILE_SIZE = 1024 * 1024

class RepositoryScanner:
    """Сканер репозитория"""
    
    def __init__(self, repo_path: str = "/data/documentation"):
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
    
    def get_documentation_chunks(self) -> List[Dict]:
        """
        Parse markdown files from documentation directory into chunks.
        
        Returns:
            List of chunk dictionaries from documentation/*.md files
        """
        import asyncio
        from src.chunker import CodeChunker
        
        logger.info("Starting documentation indexing...")
        chunks = []
        
        # Индексируем файлы из /data/documentation
        doc_dir = Path("/data/documentation")
        if not doc_dir.exists():
            logger.warning(f"Documentation directory not found: {doc_dir}")
            return []
        
        md_files = list(doc_dir.glob("*.md"))
        logger.info(f"Found {len(md_files)} markdown files")
        
        for md_file in md_files:
            try:
                content = md_file.read_text(encoding='utf-8')
                rel_path = str(md_file.relative_to(Path("/data")))
                
                # Разбиваем на чанки по секциям
                file_chunks = CodeChunker.chunk_markdown_by_sections(content, rel_path)
                
                # Добавляем метаданные к каждому чанку
                for chunk in file_chunks:
                    chunk['source'] = rel_path
                    chunk['file'] = rel_path  # Для совместимости с hybrid_search
                    chunk['file_type'] = 'markdown'
                
                chunks.extend(file_chunks)
                logger.info(f"Indexed {md_file.name}: {len(file_chunks)} chunks")
                
            except Exception as e:
                logger.error(f"Error indexing {md_file}: {e}")
        
        # Индексируем data.json из tetepfgr
        data_json_path = Path("/data/repo/tetepfgr/data.json")
        if data_json_path.exists():
            try:
                import json
                content = data_json_path.read_text(encoding='utf-8')
                rel_path = "tetepfgr/data.json"
                
                # Разбиваем JSON на чанки
                file_chunks = CodeChunker.chunk_json(content, rel_path)
                
                for chunk in file_chunks:
                    chunk['source'] = rel_path
                    chunk['file'] = rel_path  # Для совместимости с hybrid_search
                    chunk['file_type'] = 'json'
                
                chunks.extend(file_chunks)
                logger.info(f"Indexed data.json: {len(file_chunks)} chunks")
                
            except Exception as e:
                logger.error(f"Error indexing data.json: {e}")
        
        logger.info(f"Total documentation chunks: {len(chunks)}")
        return chunks
