"""
Модуль индексации файлов репозитория
"""
import os
import hashlib
from pathlib import Path
from typing import List, Dict, Set
import logging

logger = logging.getLogger(__name__)

# Импортируем парсер документации
try:
    import sys
    from pathlib import Path as SysPath
    # Добавляем родительскую директорию в путь для импорта parsers
    parent_dir = str(SysPath(__file__).parent.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    from parsers.documentation_parser import parse_documentation_files
    PARSER_AVAILABLE = True
except ImportError:
    PARSER_AVAILABLE = False
    logger.warning("Documentation parser not available")

# Чёрный список папок
EXCLUDED_DIRS = {
    '.git', 'node_modules', '__pycache__', 'logs',
    'chroma_data', 'ollama_data', 'redis_data',
    '.vscode', '.idea', 'dist', 'build', 'target',
    '.next', '.nuxt', 'coverage', '.pytest_cache',
    'screenshots', '.history', '.cursor', '.husky',
    '.storybook', 'migrations', 'tests', 'test',
    '.docker', '.bin', 'monitoring', 'telemetry-visualizer'
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
        Parse ONLY documentation directory files (markdown, txt).
        NO data.json, NO directory_data.json - ONLY from documentation/ folder.
        
        Returns:
            List of chunk dictionaries from documentation/ directory ONLY
        """
        if not PARSER_AVAILABLE:
            logger.warning("Documentation parser not available, skipping documentation parsing")
            return []
        
        # Path to documentation directory - ONLY source of truth
        # documentation/ is at same level as tetepfgr/, so go up one level from repo
        documentation_dir = self.repo_path.parent / 'documentation'
        
        all_chunks = []
        
        # Parse ONLY markdown and text files from documentation directory
        if documentation_dir.exists() and documentation_dir.is_dir():
            try:
                logger.info(f"📚 Parsing documentation directory: {documentation_dir}")
                logger.info("⚠️  Using ONLY documentation/ folder - NO data.json or directory_data.json!")
                
                # Find all markdown and text files
                doc_files = list(documentation_dir.glob('*.md')) + list(documentation_dir.glob('*.txt'))
                logger.info(f"Found {len(doc_files)} documentation files")
                
                for doc_file in doc_files:
                    try:
                        from parsers.documentation_parser import parse_markdown_file
                        doc_chunks = parse_markdown_file(str(doc_file))
                        all_chunks.extend(doc_chunks)
                        logger.info(f"✅ {doc_file.name}: {len(doc_chunks)} chunks")
                    except Exception as e:
                        logger.error(f"Error parsing {doc_file.name}: {e}")
            except Exception as e:
                logger.error(f"Error scanning documentation directory: {e}")
        else:
            logger.error(f"❌ Documentation directory NOT found: {documentation_dir}")
        
        logger.info(f" Total documentation chunks: {len(all_chunks)}")
        return all_chunks
