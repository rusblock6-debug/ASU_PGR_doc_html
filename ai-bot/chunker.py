"""
Модуль разбиения файлов на чанки
"""
import ast
import re
from pathlib import Path
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class CodeChunker:
    """Разбиение кода на смысловые чанки"""
    
    @staticmethod
    def chunk_python(content: str, file_path: str) -> List[Dict]:
        """Разбиение Python-кода на функции и классы"""
        chunks = []
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    # Получаем исходный код функции/класса
                    start_line = node.lineno
                    end_line = node.end_lineno or start_line
                    
                    lines = content.split('\n')
                    chunk_content = '\n'.join(lines[start_line-1:end_line])
                    
                    chunks.append({
                        'content': chunk_content,
                        'type': 'function' if isinstance(node, ast.FunctionDef) else 'class',
                        'name': node.name,
                        'file': file_path,
                        'line_start': start_line,
                        'line_end': end_line
                    })
        except SyntaxError as e:
            logger.warning(f"Ошибка парсинга Python {file_path}: {e}")
            # Fallback: разбиваем по параграфам
            chunks = CodeChunker.chunk_by_paragraphs(content, file_path)
        
        return chunks
    
    @staticmethod
    def chunk_javascript(content: str, file_path: str) -> List[Dict]:
        """Разбиение JS/TS на функции и компоненты"""
        chunks = []
        
        # Простой regex-парсинг (для полноценного нужен Tree-sitter)
        # Ищем функции: function name() { ... }
        function_pattern = r'(function\s+\w+\s*\([^)]*\)\s*\{[^}]*\})'
        # Ищем стрелочные функции: const name = () => { ... }
        arrow_pattern = r'(const\s+\w+\s*=\s*\([^)]*\)\s*=>\s*\{[^}]*\})'
        
        for match in re.finditer(function_pattern, content):
            chunks.append({
                'content': match.group(1),
                'type': 'function',
                'file': file_path,
                'line_start': content[:match.start()].count('\n') + 1
            })
        
        for match in re.finditer(arrow_pattern, content):
            chunks.append({
                'content': match.group(1),
                'type': 'function',
                'file': file_path,
                'line_start': content[:match.start()].count('\n') + 1
            })
        
        # Если ничего не нашли, разбиваем по параграфам
        if not chunks:
            chunks = CodeChunker.chunk_by_paragraphs(content, file_path)
        
        return chunks
    
    @staticmethod
    def chunk_sql(content: str, file_path: str) -> List[Dict]:
        """Разбиение SQL на отдельные запросы"""
        chunks = []
        
        # Разбиваем по точке с запятой
        statements = content.split(';')
        
        line_num = 1
        for stmt in statements:
            stmt = stmt.strip()
            if stmt:
                chunks.append({
                    'content': stmt,
                    'type': 'sql_statement',
                    'file': file_path,
                    'line_start': line_num
                })
                line_num += stmt.count('\n') + 1
        
        return chunks
    
    @staticmethod
    def chunk_json(content: str, file_path: str) -> List[Dict]:
        """Разбиение JSON на объекты верхнего уровня"""
        import json
        
        chunks = []
        
        try:
            data = json.loads(content)
            
            if isinstance(data, dict):
                # Если это объект, разбиваем по ключам верхнего уровня
                for key, value in data.items():
                    chunks.append({
                        'content': json.dumps({key: value}, ensure_ascii=False, indent=2),
                        'type': 'json_object',
                        'name': key,
                        'file': file_path
                    })
            elif isinstance(data, list):
                # Если это массив, каждый элемент — отдельный чанк
                for i, item in enumerate(data):
                    chunks.append({
                        'content': json.dumps(item, ensure_ascii=False, indent=2),
                        'type': 'json_array_item',
                        'name': f'item_{i}',
                        'file': file_path
                    })
        except json.JSONDecodeError as e:
            logger.warning(f"Ошибка парсинга JSON {file_path}: {e}")
            chunks = [{'content': content, 'type': 'text', 'file': file_path}]
        
        return chunks
    
    @staticmethod
    def chunk_by_paragraphs(content: str, file_path: str, max_size: int = 1000) -> List[Dict]:
        """Разбиение текста по параграфам"""
        chunks = []
        paragraphs = content.split('\n\n')
        
        current_chunk = ""
        line_start = 1
        
        for para in paragraphs:
            if len(current_chunk) + len(para) > max_size and current_chunk:
                chunks.append({
                    'content': current_chunk.strip(),
                    'type': 'paragraph',
                    'file': file_path,
                    'line_start': line_start
                })
                current_chunk = para
                line_start += current_chunk.count('\n')
            else:
                current_chunk += '\n\n' + para if current_chunk else para
        
        if current_chunk:
            chunks.append({
                'content': current_chunk.strip(),
                'type': 'paragraph',
                'file': file_path,
                'line_start': line_start
            })
        
        return chunks
    
    @staticmethod
    def chunk_file(file_path: str, content: str) -> List[Dict]:
        """Разбиение файла на чанки в зависимости от типа"""
        ext = Path(file_path).suffix.lower()
        
        if ext == '.py':
            return CodeChunker.chunk_python(content, file_path)
        elif ext in ['.js', '.jsx', '.ts', '.tsx']:
            return CodeChunker.chunk_javascript(content, file_path)
        elif ext == '.sql':
            return CodeChunker.chunk_sql(content, file_path)
        elif ext == '.json':
            return CodeChunker.chunk_json(content, file_path)
        elif ext in ['.md', '.txt', '.html']:
            return CodeChunker.chunk_by_paragraphs(content, file_path)
        else:
            # Для остальных — один чанк на файл
            return [{
                'content': content,
                'type': 'file',
                'file': file_path
            }]
