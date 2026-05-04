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
    
    def get_documentation_chunks(self) -> List[Dict]:
        """
        Parse documentation JSON files and markdown files into chunks.
        
        Returns:
            List of chunk dictionaries from data.json, directory_data.json and documentation/*.md
        """
        if not PARSER_AVAILABLE:
            logger.warning("Documentation parser not available, skipping documentation parsing")
            return []
        
        # Paths to documentation files
        # repo_path is /data/repo which maps to tetepfgr/ folder on host
        data_json = self.repo_path / 'data.json'
        directory_data = self.repo_path / 'directory_data.json'
        
        # Path to documentation directory (markdown files)
        # documentation/ is at same level as tetepfgr/, so go up one level from repo
        documentation_dir = self.repo_path.parent / 'documentation'
        
        all_chunks = []
        
        # Parse JSON files if they exist
        if data_json.exists() and directory_data.exists():
            try:
                logger.info("Parsing JSON documentation files...")
                json_chunks = parse_documentation_files(
                    str(data_json), 
                    str(directory_data),
                    None  # Don't pass documentation_dir here, we'll handle it separately
                )
                all_chunks.extend(json_chunks)
                logger.info(f"Parsed {len(json_chunks)} JSON documentation chunks")
            except Exception as e:
                logger.error(f"Error parsing JSON files: {e}")
        else:
            if not data_json.exists():
                logger.warning(f"data.json not found: {data_json}")
            if not directory_data.exists():
                logger.warning(f"directory_data.json not found: {directory_data}")
        
        # Parse markdown files from documentation directory
        if documentation_dir.exists() and documentation_dir.is_dir():
            try:
                logger.info(f"Scanning documentation directory: {documentation_dir}")
                md_files = list(documentation_dir.glob('*.md'))
                logger.info(f"Found {len(md_files)} markdown files")
                
                for md_file in md_files:
                    try:
                        from parsers.documentation_parser import parse_markdown_file
                        md_chunks = parse_markdown_file(str(md_file))
                        all_chunks.extend(md_chunks)
                        logger.info(f"✅ {md_file.name}: {len(md_chunks)} chunks")
                    except Exception as e:
                        logger.error(f"Error parsing {md_file.name}: {e}")
            except Exception as e:
                logger.error(f"Error scanning documentation directory: {e}")
        
        logger.info(f"Total documentation chunks: {len(all_chunks)}")
        return all_chunks
