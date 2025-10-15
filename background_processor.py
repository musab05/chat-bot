import threading
import json
import os
from datetime import datetime
from mainprocessor import LessonProcessor
from utils import save_lesson_metadata

class BackgroundProcessor:
    def __init__(self, upload_folder):
        self.upload_folder = upload_folder
        self.lesson_processor = LessonProcessor()
        self.processing_status = {}
    
    def process_video_async(self, lesson_key, file_path, filename, callback=None):
        """Process video in background thread"""
        self.processing_status[lesson_key] = {
            'status': 'processing',
            'progress': 0,
            'message': 'Starting video processing...'
        }
        
        thread = threading.Thread(
            target=self._process_video_worker,
            args=(lesson_key, file_path, filename, callback)
        )
        thread.daemon = True
        thread.start()
        
        return lesson_key
    
    def _process_video_worker(self, lesson_key, file_path, filename, callback):
        try:
            # Update status
            self.processing_status[lesson_key].update({
                'progress': 20,
                'message': 'Extracting audio...'
            })
            
            # Process video
            lesson_data = self.lesson_processor.process_video(file_path, filename)
            
            self.processing_status[lesson_key].update({
                'progress': 80,
                'message': 'Finalizing...'
            })
            
            # Save lesson data
            lesson_data['lesson_key'] = lesson_key
            lesson_data['uploaded_at'] = datetime.now().isoformat()
            lesson_data['source_type'] = 'file'
            lesson_data['source'] = filename
            
            lesson_file = os.path.join(self.upload_folder, f"{lesson_key}.json")
            with open(lesson_file, 'w', encoding='utf-8') as f:
                json.dump(lesson_data, f, ensure_ascii=False, indent=2)
            
            save_lesson_metadata(lesson_key, lesson_data)
            
            # Mark as complete
            self.processing_status[lesson_key] = {
                'status': 'completed',
                'progress': 100,
                'message': 'Processing complete!',
                'lesson_data': lesson_data
            }
            
            if callback:
                callback(lesson_key, lesson_data)
                
        except Exception as e:
            self.processing_status[lesson_key] = {
                'status': 'failed',
                'progress': 0,
                'message': f'Error: {str(e)}'
            }
    
    def get_status(self, lesson_key):
        return self.processing_status.get(lesson_key, {'status': 'not_found'})
    
    def cleanup_status(self, lesson_key):
        if lesson_key in self.processing_status:
            del self.processing_status[lesson_key]