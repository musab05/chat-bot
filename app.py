from flask import Flask, render_template, request, jsonify, session
import os
import json
import uuid
import tempfile
from pathlib import Path
from datetime import datetime
import logging
from werkzeug.utils import secure_filename

from mainprocessor import LessonProcessor, EnhancedRAGChatbot, QuizGenerator
from utils import allowed_file, save_lesson_metadata, get_all_lessons
from background_processor import BackgroundProcessor

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
app.secret_key = 'your-secret-key-change-in-production'

# Force reload after fixing beam_size error

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

lesson_processor = LessonProcessor()
rag_chatbot = EnhancedRAGChatbot()
quiz_generator = QuizGenerator()
background_processor = BackgroundProcessor(app.config['UPLOAD_FOLDER'])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_user_id():
    """Get or create user ID for session tracking"""
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    return session['user_id']

@app.route('/')
def index():
    return render_template('upload.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'GET':
        return render_template('upload.html')
    
    try:
        lesson_key = str(uuid.uuid4())
        youtube_url = request.form.get('youtube_url', '').strip()
        uploaded_file = request.files.get('file')
        
        if youtube_url:
            lesson_data = lesson_processor.process_youtube_url(youtube_url)
            lesson_data['source_type'] = 'youtube'
            lesson_data['source'] = youtube_url
        elif uploaded_file and uploaded_file.filename and allowed_file(uploaded_file.filename):
            filename = secure_filename(uploaded_file.filename)
            file_ext = Path(filename).suffix.lower()
            
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=file_ext)
            try:
                with os.fdopen(tmp_fd, 'wb') as tmp_file:
                    uploaded_file.save(tmp_file)
                
                if file_ext == '.txt':
                    with open(tmp_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    lesson_data = lesson_processor.process_text_file(content, filename)
                elif file_ext == '.pdf':
                    lesson_data = lesson_processor.process_pdf(tmp_path, filename)
                elif file_ext == '.docx':
                    lesson_data = lesson_processor.process_docx(tmp_path, filename)
                elif file_ext in ['.mp4', '.avi', '.mov', '.wav', '.mp3']:
                    background_processor.process_video_async(lesson_key, tmp_path, filename)
                    return jsonify({
                        'success': True,
                        'lesson_key': lesson_key,
                        'title': filename,
                        'processing': True,
                        'message': 'Video processing started in background. Check status for updates.'
                    })
                else:
                    return jsonify({'error': 'Unsupported file format'}), 400
                    
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                
            lesson_data['source_type'] = 'file'
            lesson_data['source'] = filename
        else:
            return jsonify({'error': 'No valid file or YouTube URL provided'}), 400
        
        lesson_data['lesson_key'] = lesson_key
        lesson_data['uploaded_at'] = datetime.now().isoformat()
        
        lesson_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{lesson_key}.json")
        with open(lesson_file, 'w', encoding='utf-8') as f:
            json.dump(lesson_data, f, ensure_ascii=False, indent=2)
        
        save_lesson_metadata(lesson_key, lesson_data)
        rag_chatbot.load_lesson(lesson_data)
        
        return jsonify({
            'success': True,
            'lesson_key': lesson_key,
            'title': lesson_data['title'],
            'message': 'Lesson processed successfully!'
        })
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/chat')
def chat():
    lessons = get_all_lessons()
    user_id = get_user_id()
    return render_template('chat.html', lessons=lessons, user_id=user_id)

@app.route('/api/chat', methods=['POST'])
def api_chat():
    try:
        data = request.get_json()
        lesson_key = data.get('lesson_key')
        message = data.get('message')
        user_id = get_user_id()
        
        if not lesson_key or not message:
            return jsonify({'error': 'Missing lesson_key or message'}), 400
        
        lesson_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{lesson_key}.json")
        if not os.path.exists(lesson_file):
            return jsonify({'error': 'Lesson not found'}), 404
        
        with open(lesson_file, 'r', encoding='utf-8') as f:
            lesson_data = json.load(f)
        
        rag_chatbot.load_lesson(lesson_data)
        response = rag_chatbot.chat(message, user_id)
        
        return jsonify({
            'response': response,
            'lesson_title': lesson_data['title'],
            'user_id': user_id
        })
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/analytics/<user_id>')
def get_chat_analytics(user_id):
    """Get user learning analytics"""
    try:
        analytics = rag_chatbot.get_user_analytics(user_id)
        return jsonify(analytics)
    except Exception as e:
        logger.error(f"Analytics error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/lesson/insights/<lesson_key>')
def get_lesson_insights(lesson_key):
    """Get lesson content insights"""
    try:
        lesson_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{lesson_key}.json")
        if not os.path.exists(lesson_file):
            return jsonify({'error': 'Lesson not found'}), 404
        
        with open(lesson_file, 'r', encoding='utf-8') as f:
            lesson_data = json.load(f)
        
        rag_chatbot.load_lesson(lesson_data)
        insights = rag_chatbot.get_lesson_insights()
        
        return jsonify(insights)
        
    except Exception as e:
        logger.error(f"Insights error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/adaptive', methods=['POST'])
def adaptive_explanation():
    """Generate adaptive explanation based on user preferences"""
    try:
        data = request.get_json()
        lesson_key = data.get('lesson_key')
        topic = data.get('topic')
        complexity = data.get('complexity', 'medium')
        intent = data.get('intent', 'explanation')
        user_id = get_user_id()
        
        if not lesson_key or not topic:
            return jsonify({'error': 'Missing lesson_key or topic'}), 400
        
        lesson_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{lesson_key}.json")
        if not os.path.exists(lesson_file):
            return jsonify({'error': 'Lesson not found'}), 404
        
        with open(lesson_file, 'r', encoding='utf-8') as f:
            lesson_data = json.load(f)
        
        rag_chatbot.load_lesson(lesson_data)
        
        relevant_chunks = rag_chatbot.semantic_search(topic)
        content = "\n\n".join(relevant_chunks)
        
        explanation = rag_chatbot.adaptive_explainer.generate_adaptive_explanation(
            content, topic, complexity, intent
        )
        
        rag_chatbot.learning_analytics.track_interaction(user_id, intent, topic, complexity)
        
        return jsonify({
            'explanation': explanation,
            'complexity': complexity,
            'intent': intent,
            'topic': topic
        })
        
    except Exception as e:
        logger.error(f"Adaptive explanation error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/quiz')
def quiz():
    lessons = get_all_lessons()
    return render_template('quiz.html', lessons=lessons)

@app.route('/api/quiz/generate', methods=['POST'])
def generate_quiz():
    try:
        data = request.get_json()
        lesson_key = data.get('lesson_key')
        num_questions = int(data.get('num_questions', 5))
        difficulty = data.get('difficulty', 'medium')
        
        if not lesson_key:
            return jsonify({'error': 'Missing lesson_key'}), 400
        
        lesson_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{lesson_key}.json")
        if not os.path.exists(lesson_file):
            return jsonify({'error': 'Lesson not found'}), 404
        
        with open(lesson_file, 'r', encoding='utf-8') as f:
            lesson_data = json.load(f)
        
        questions = quiz_generator.generate_quiz(
            lesson_data['content'], 
            num_questions=num_questions, 
            difficulty=difficulty
        )
        
        return jsonify({
            'questions': questions,
            'lesson_title': lesson_data['title']
        })
        
    except Exception as e:
        logger.error(f"Quiz generation error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/quiz/evaluate', methods=['POST'])
def evaluate_quiz():
    try:
        data = request.get_json()
        questions = data.get('questions')
        answers = data.get('answers')
        
        if not questions or not answers:
            return jsonify({'error': 'Missing questions or answers'}), 400
        
        results = []
        correct_count = 0
        
        for i, (question, answer) in enumerate(zip(questions, answers)):
            evaluation = quiz_generator.evaluate_answer(question, answer)
            results.append(evaluation)
            if evaluation['correct']:
                correct_count += 1
        
        score = (correct_count / len(questions)) * 100
        
        return jsonify({
            'results': results,
            'score': score,
            'correct_count': correct_count,
            'total_questions': len(questions)
        })
        
    except Exception as e:
        logger.error(f"Quiz evaluation error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/status/<lesson_key>')
def get_processing_status(lesson_key):
    """Get processing status for background jobs"""
    status = background_processor.get_status(lesson_key)
    return jsonify(status)

@app.route('/analytics')
def analytics_dashboard():
    """Analytics dashboard"""
    user_id = get_user_id()
    analytics = rag_chatbot.get_user_analytics(user_id)
    lessons = get_all_lessons()
    
    return render_template('analytics.html', analytics=analytics, lessons=lessons, user_id=user_id)

@app.route('/api/debug/lessons')
def debug_lessons():
    """Debug endpoint to check lessons"""
    lessons = get_all_lessons()
    return jsonify({
        'count': len(lessons),
        'lessons': lessons
    })

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=3001)