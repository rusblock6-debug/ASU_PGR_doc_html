"""
Модуль разбиения файлов на чанки (гибридный подход)
"""
import ast
import re
from pathlib import Path
from typing import List, Dict, Optional
import logging
import httpx
import os
import json

logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")

class CodeChunker:
    """Разбиение кода на смысловые чанки (гибридный подход)"""
    
    @staticmethod
    async def chunk_with_phi4(content: str, file_path: str, file_type: str) -> Optional[List[Dict]]:
        """
        Умное чанкование через Phi-4-mini для сложных файлов
        
        Args:
            content: Содержимое файла
            file_path: Путь к файлу
            file_type: Тип файла (markdown, yaml, config, etc.)
        
        Returns:
            Список чанков или None если не удалось
        """
        try:
            prompt = f"""Ты — эксперт по анализу технической документации.

Задача: Разбей этот {file_type} файл на логические смысловые блоки.

Правила:
1. Каждый блок должен быть самодостаточным (можно понять отдельно)
2. Размер блока: 200-800 слов
3. Сохраняй контекст (заголовки, описания)
4. Для кода: группируй связанные функции/классы
5. Для документации: группируй по темам/разделам

Файл: {file_path}

Содержимое:
```
{content[:4000]}  # Ограничиваем для скорости
```

Верни JSON массив чанков в формате:
[
  {{"content": "текст блока 1", "title": "краткое название", "type": "тип блока"}},
  {{"content": "текст блока 2", "title": "краткое название", "type": "тип блока"}}
]

ВАЖНО: Верни ТОЛЬКО JSON, без дополнительного текста!"""

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{OLLAMA_URL}/api/generate",
                    json={
                        "model": "phi4-mini",
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,  # Низкая температура для точности
                            "top_p": 0.9,
                            "max_tokens": 2000
                        }
                    }
                )
                
                if response.status_code != 200:
                    logger.warning(f"Phi-4 chunking failed for {file_path}: {response.status_code}")
                    return None
                
                result = response.json()
                answer = result.get('response', '').strip()
                
                # Извлекаем JSON из ответа
                json_match = re.search(r'\[.*\]', answer, re.DOTALL)
                if not json_match:
                    logger.warning(f"No JSON found in Phi-4 response for {file_path}")
                    return None
                
                chunks_data = json.loads(json_match.group(0))
                
                # Преобразуем в нужный формат
                chunks = []
                for i, chunk_data in enumerate(chunks_data):
                    chunks.append({
                        'content': chunk_data.get('content', ''),
                        'type': chunk_data.get('type', 'phi4_chunk'),
                        'name': chunk_data.get('title', f'chunk_{i}'),
                        'file': file_path,
                        'line_start': 1,  # Phi-4 не знает точных строк
                        'chunked_by': 'phi4-mini'
                    })
                
                logger.info(f"✨ Phi-4 chunked {file_path}: {len(chunks)} chunks")
                return chunks
                
        except Exception as e:
            logger.warning(f"Phi-4 chunking error for {file_path}: {e}")
            return None
    
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
    async def chunk_file_async(file_path: str, content: str, use_phi4: bool = True) -> List[Dict]:
        """
        Разбиение файла на чанки (гибридный подход)
        
        Args:
            file_path: Путь к файлу
            content: Содержимое файла
            use_phi4: Использовать ли Phi-4 для сложных файлов
        
        Returns:
            Список чанков
        """
        ext = Path(file_path).suffix.lower()
        
        # Быстрое чанкование для кода (Tree-sitter/AST)
        if ext == '.py':
            return CodeChunker.chunk_python(content, file_path)
        elif ext in ['.js', '.jsx', '.ts', '.tsx']:
            return CodeChunker.chunk_javascript(content, file_path)
        elif ext == '.sql':
            return CodeChunker.chunk_sql(content, file_path)
        
        # Умное чанкование для документации и конфигов (Phi-4)
        if use_phi4 and ext in ['.md', '.yaml', '.yml', '.json', '.html', '.txt']:
            file_type_map = {
                '.md': 'Markdown документация',
                '.yaml': 'YAML конфигурация',
                '.yml': 'YAML конфигурация',
                '.json': 'JSON данные',
                '.html': 'HTML документация',
                '.txt': 'текстовый файл'
            }
            file_type = file_type_map.get(ext, 'файл')
            
            # Пробуем Phi-4
            phi4_chunks = await CodeChunker.chunk_with_phi4(content, file_path, file_type)
            if phi4_chunks:
                return phi4_chunks
            
            # Fallback: если Phi-4 не справился
            logger.info(f"Fallback to simple chunking for {file_path}")
        
        # Простое чанкование для остальных
        if ext == '.json':
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
    
    @staticmethod
    def chunk_file(file_path: str, content: str) -> List[Dict]:
        """
        Синхронная обёртка для chunk_file_async (для обратной совместимости)
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            CodeChunker.chunk_file_async(file_path, content, use_phi4=True)
        )
