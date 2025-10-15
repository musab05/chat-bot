import os
import json
from typing import Dict, List, Any

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'mp4', 'avi', 'mov', 'wav', 'mp3'}
DB_FILE = 'lessons_db.json'

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_lesson_metadata(lesson_key: str, lesson_data: Dict[str, Any]):
    """Save lesson metadata to JSON database"""
    db_data = load_db()
    
    db_data[lesson_key] = {
        'title': lesson_data['title'],
        'type': lesson_data['type'],
        'source_type': lesson_data.get('source_type', 'unknown'),
        'source': lesson_data.get('source', ''),
        'uploaded_at': lesson_data['uploaded_at'],
        'processed_at': lesson_data['processed_at']
    }
    
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(db_data, f, ensure_ascii=False, indent=2)

def load_db() -> Dict[str, Any]:
    """Load lessons database"""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def get_all_lessons() -> List[Dict[str, Any]]:
    """Get all lessons from database"""
    db_data = load_db()
    lessons = []
    
    for lesson_key, metadata in db_data.items():
        lessons.append({
            'lesson_key': lesson_key,
            **metadata
        })
    
    # Sort by upload time (newest first)
    lessons.sort(key=lambda x: x.get('uploaded_at', ''), reverse=True)
    return lessons

def load_lesson_metadata(lesson_key: str) -> Dict[str, Any]:
    """Load specific lesson metadata"""
    db_data = load_db()
    return db_data.get(lesson_key, {})