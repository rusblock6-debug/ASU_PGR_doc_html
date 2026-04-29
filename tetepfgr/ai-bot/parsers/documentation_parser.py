"""
Documentation parser for ASU PGR RAG bot.

Parses data.json and directory_data.json into text chunks for indexing.
"""

import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def parse_data_json(file_path: str) -> List[Dict[str, Any]]:
    """Parse data.json file into text chunks."""
    logger.info(f"Parsing data.json: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
    
    chunks = []
    cards = data.get('cards', {})
    
    if 'quickstart' in cards:
        quickstart_chunks = _parse_quickstart(cards['quickstart'], file_path)
        chunks.extend(quickstart_chunks)
        logger.info(f"  Quickstart: {len(quickstart_chunks)} chunks")
    
    if 'descriptive' in cards:
        descriptive_chunks = _parse_descriptive(cards['descriptive'], file_path)
        chunks.extend(descriptive_chunks)
        logger.info(f"  Descriptive: {len(descriptive_chunks)} chunks")
    
    if 'instructions' in cards:
        instructions_chunks = _parse_instructions(cards['instructions'], file_path)
        chunks.extend(instructions_chunks)
        logger.info(f"  Instructions: {len(instructions_chunks)} chunks")
    
    if 'admin_instructions' in cards:
        admin_chunks = _parse_admin_instructions(cards['admin_instructions'], file_path)
        chunks.extend(admin_chunks)
        logger.info(f"  Admin instructions: {len(admin_chunks)} chunks")
    
    logger.info(f"Total chunks from data.json: {len(chunks)}")
    return chunks


def _parse_quickstart(quickstart_data: Dict, file_path: str) -> List[Dict[str, Any]]:
    """Parse quickstart section into chunks."""
    chunks = []
    
    title = quickstart_data.get('title', 'Быстрый старт')
    description = quickstart_data.get('description', '')
    steps = quickstart_data.get('steps', [])
    
    content_parts = [f"[ЗАГОЛОВОК] {title}"]
    
    if description:
        content_parts.append(f"\n[ОПИСАНИЕ] {description}")
    
    if steps:
        content_parts.append("\n[ШАГИ]")
        for step_idx, step in enumerate(steps, 1):
            step_text = _format_step(step, indent_level=0)
            content_parts.append(step_text)
    
    content = "\n".join(content_parts)
    
    chunk = {
        'content': content,
        'metadata': {
            'source': 'JSON',
            'file': file_path,
            'type': 'quickstart',
            'id': 'quickstart',
            'section': 'Быстрый старт'
        }
    }
    
    chunks.append(chunk)
    return chunks


def _parse_descriptive(descriptive_list: List[Dict], file_path: str) -> List[Dict[str, Any]]:
    """Parse descriptive cards into chunks."""
    chunks = []
    
    for card in descriptive_list:
        title = card.get('title', '')
        description = card.get('description', '')
        items = card.get('items', [])
        
        if not title:
            continue
        
        content_parts = [f"[ЗАГОЛОВОК] {title}"]
        
        if description:
            content_parts.append(f"\n[ОПИСАНИЕ] {description}")
        
        if items:
            content_parts.append("\n[СОДЕРЖАНИЕ]")
            for item in items:
                if isinstance(item, dict):
                    item_text = _format_item(item)
                    content_parts.append(item_text)
                elif isinstance(item, str):
                    content_parts.append(f"- {item}")
        
        content = "\n".join(content_parts)
        chunk_id = _generate_id(title)
        
        chunk = {
            'content': content,
            'metadata': {
                'source': 'JSON',
                'file': file_path,
                'type': 'descriptive',
                'id': chunk_id,
                'section': title
            }
        }
        
        chunks.append(chunk)
    
    return chunks


def _parse_instructions(instructions_list: List[Dict], file_path: str) -> List[Dict[str, Any]]:
    """Parse instructions into chunks."""
    chunks = []
    
    for instruction in instructions_list:
        title = instruction.get('title', '')
        description = instruction.get('description', '')
        steps = instruction.get('steps', [])
        key_indicators = instruction.get('keyIndicators', [])
        
        if not title:
            continue
        
        content_parts = [f"[ЗАГОЛОВОК] {title}"]
        
        if description:
            content_parts.append(f"\n[ОПИСАНИЕ] {description}")
        
        if steps:
            content_parts.append("\n[ШАГИ]")
            for step_idx, step in enumerate(steps, 1):
                step_text = _format_step(step, indent_level=0)
                content_parts.append(step_text)
        
        if key_indicators:
            content_parts.append("\n[КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ]")
            for indicator in key_indicators:
                content_parts.append(f"- {indicator}")
        
        content = "\n".join(content_parts)
        chunk_id = _generate_id(title)
        
        chunk = {
            'content': content,
            'metadata': {
                'source': 'JSON',
                'file': file_path,
                'type': 'instruction',
                'id': chunk_id,
                'section': title
            }
        }
        
        chunks.append(chunk)
    
    return chunks


def _parse_admin_instructions(admin_list: List[Dict], file_path: str) -> List[Dict[str, Any]]:
    """Parse admin instructions into chunks."""
    chunks = []
    
    for instruction in admin_list:
        title = instruction.get('title', '')
        description = instruction.get('description', '')
        steps = instruction.get('steps', [])
        key_indicators = instruction.get('keyIndicators', [])
        
        if not title:
            continue
        
        content_parts = [f"[ЗАГОЛОВОК] {title}"]
        
        if description:
            content_parts.append(f"\n[ОПИСАНИЕ] {description}")
        
        if steps:
            content_parts.append("\n[ШАГИ]")
            for step_idx, step in enumerate(steps, 1):
                step_text = _format_step(step, indent_level=0)
                content_parts.append(step_text)
        
        if key_indicators:
            content_parts.append("\n[КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ]")
            for indicator in key_indicators:
                content_parts.append(f"- {indicator}")
        
        content = "\n".join(content_parts)
        chunk_id = instruction.get('id', _generate_id(title))
        
        chunk = {
            'content': content,
            'metadata': {
                'source': 'JSON',
                'file': file_path,
                'type': 'admin_instruction',
                'id': chunk_id,
                'section': title
            }
        }
        
        chunks.append(chunk)
    
    return chunks


def _format_step(step: Dict, indent_level: int = 0) -> str:
    """Format a step with substeps recursively."""
    lines = []
    indent = "  " * indent_level
    
    step_title = step.get('title', '')
    if step_title:
        lines.append(f"{indent}{step_title}")
    
    substeps = step.get('substeps', [])
    if substeps:
        for substep in substeps:
            if isinstance(substep, dict):
                substep_lines = _format_substep(substep, indent_level + 1)
                lines.extend(substep_lines)
            elif isinstance(substep, str):
                lines.append(f"{indent}  {substep}")
    
    details = step.get('details', [])
    if details:
        for detail in details:
            lines.append(f"{indent}  {detail}")
    
    return "\n".join(lines)


def _format_substep(substep: Dict, indent_level: int) -> List[str]:
    """Format a substep with text, details, and images."""
    lines = []
    indent = "  " * indent_level
    
    text = substep.get('text', '')
    if text:
        lines.append(f"{indent}{text}")
    
    details = substep.get('details', [])
    if details:
        for detail in details:
            lines.append(f"{indent}  {detail}")
    
    images = substep.get('images', [])
    if images:
        lines.append(f"{indent}  [Изображения: {len(images)} скриншот(ов)]")
    
    return lines


def _format_item(item: Dict) -> str:
    """Format a descriptive item."""
    lines = []
    
    text = item.get('text', '')
    if text:
        lines.append(f"- {text}")
    
    details = item.get('details', [])
    if details:
        for detail in details:
            lines.append(f"  {detail}")
    
    return "\n".join(lines)


def _generate_id(title: str) -> str:
    """Generate a chunk ID from title."""
    id_str = title.lower()
    id_str = re.sub(r'[^\w\s-]', '', id_str)
    id_str = re.sub(r'[\s-]+', '_', id_str)
    id_str = id_str.strip('_')
    return id_str


def parse_directory_data_json(file_path: str) -> List[Dict[str, Any]]:
    """Parse directory_data.json file into text chunks."""
    logger.info(f"Parsing directory_data.json: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
    
    chunks = []
    directories = data.get('directories', {})
    
    for dir_key, dir_data in directories.items():
        title = dir_data.get('title', '')
        parameters = dir_data.get('parameters', '')
        note = dir_data.get('note', '')
        image = dir_data.get('image', '')
        
        if not title:
            continue
        
        content_parts = [f"[ЗАГОЛОВОК] {title}"]
        
        if parameters:
            content_parts.append(f"\n[ПАРАМЕТРЫ] {parameters}")
        
        if note:
            content_parts.append(f"\n[ПРИМЕЧАНИЕ] {note}")
        
        if image:
            content_parts.append(f"\n[ИЗОБРАЖЕНИЕ] {image}")
        
        content = "\n".join(content_parts)
        
        chunk = {
            'content': content,
            'metadata': {
                'source': 'JSON',
                'file': file_path,
                'type': 'directory',
                'id': dir_key,
                'section': title
            }
        }
        
        chunks.append(chunk)
    
    logger.info(f"Total chunks from directory_data.json: {len(chunks)}")
    return chunks


def parse_documentation_files(data_json_path: str, directory_data_path: str) -> List[Dict[str, Any]]:
    """Parse both documentation JSON files into chunks."""
    all_chunks = []
    
    try:
        data_chunks = parse_data_json(data_json_path)
        all_chunks.extend(data_chunks)
    except Exception as e:
        logger.error(f"Error parsing data.json: {e}")
    
    try:
        dir_chunks = parse_directory_data_json(directory_data_path)
        all_chunks.extend(dir_chunks)
    except Exception as e:
        logger.error(f"Error parsing directory_data.json: {e}")
    
    logger.info(f"Total documentation chunks: {len(all_chunks)}")
    return all_chunks


if __name__ == '__main__':
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    base_path = Path(__file__).parent.parent.parent / 'tetepfgr'
    data_json = base_path / 'data.json'
    directory_data = base_path / 'directory_data.json'
    
    if len(sys.argv) > 1:
        data_json = Path(sys.argv[1])
    if len(sys.argv) > 2:
        directory_data = Path(sys.argv[2])
    
    print(f"Parsing: {data_json}")
    print(f"Parsing: {directory_data}")
    print()
    
    chunks = parse_documentation_files(str(data_json), str(directory_data))
    
    print(f"\n{'='*60}")
    print(f"TOTAL CHUNKS: {len(chunks)}")
    print(f"{'='*60}\n")
    
    for i, chunk in enumerate(chunks, 1):
        print(f"Chunk {i}:")
        print(f"  Type: {chunk['metadata']['type']}")
        print(f"  ID: {chunk['metadata']['id']}")
        print(f"  Section: {chunk['metadata']['section']}")
        print(f"  Content length: {len(chunk['content'])} chars")
        print(f"  Preview: {chunk['content'][:100]}...")
        print()
