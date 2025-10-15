import os
import sys
import tempfile
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import io
import re
from collections import Counter, defaultdict

# Add transcrib to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'transcrib'))

import PyPDF2
import docx
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk.tag import pos_tag
from nltk.chunk import ne_chunk
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import ollama
from textstat import flesch_reading_ease, flesch_kincaid_grade
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation
from textblob import TextBlob

logger = logging.getLogger(__name__)

# Download NLTK data
nltk_downloads = ['punkt', 'stopwords', 'averaged_perceptron_tagger', 'averaged_perceptron_tagger_eng', 'maxent_ne_chunker', 'maxent_ne_chunker_tab', 'words']
for item in nltk_downloads:
    try:
        nltk.download(item, quiet=True)
    except:
        pass

class ContentAnalyzer:
    def __init__(self):
        self.stop_words = set(stopwords.words('english'))
        self.tfidf = TfidfVectorizer(max_features=100, stop_words='english')
        self.lda = LatentDirichletAllocation(n_components=5, random_state=42)
    
    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Analyze sentiment of text"""
        blob = TextBlob(text)
        return {
            'polarity': blob.sentiment.polarity,  # -1 to 1
            'subjectivity': blob.sentiment.subjectivity,  # 0 to 1
            'emotion': 'positive' if blob.sentiment.polarity > 0.1 else 'negative' if blob.sentiment.polarity < -0.1 else 'neutral'
        }
    
    def extract_topics(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Extract topics using LDA"""
        if len(texts) < 2:
            return []
        
        tfidf_matrix = self.tfidf.fit_transform(texts)
        lda_output = self.lda.fit_transform(tfidf_matrix)
        
        feature_names = self.tfidf.get_feature_names_out()
        topics = []
        
        for topic_idx, topic in enumerate(self.lda.components_):
            top_words = [feature_names[i] for i in topic.argsort()[-10:][::-1]]
            topics.append({
                'topic_id': topic_idx,
                'keywords': top_words,
                'weight': float(np.max(topic))
            })
        
        return topics
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities"""
        tokens = word_tokenize(text)
        pos_tags = pos_tag(tokens)
        chunks = ne_chunk(pos_tags)
        
        entities = {'PERSON': [], 'ORGANIZATION': [], 'GPE': [], 'DATE': [], 'CONCEPT': []}
        
        for chunk in chunks:
            if hasattr(chunk, 'label'):
                entity = ' '.join([token for token, pos in chunk.leaves()])
                label = chunk.label()
                if label in entities:
                    entities[label].append(entity)
        
        # Extract concepts (nouns)
        concepts = [word for word, pos in pos_tags if pos.startswith('NN') and len(word) > 3 and word.lower() not in self.stop_words]
        entities['CONCEPT'] = list(set(concepts))[:10]
        
        return entities
    
    def extract_keywords(self, text: str, top_k: int = 10) -> List[Dict[str, float]]:
        """Extract keywords with TF-IDF"""
        tfidf_matrix = self.tfidf.fit_transform([text])
        feature_names = self.tfidf.get_feature_names_out()
        scores = tfidf_matrix.toarray()[0]
        
        keywords = []
        for i, score in enumerate(scores):
            if score > 0:
                keywords.append({'keyword': feature_names[i], 'score': float(score)})
        
        return sorted(keywords, key=lambda x: x['score'], reverse=True)[:top_k]
    
    def assess_difficulty(self, text: str) -> Dict[str, Any]:
        """Assess content difficulty"""
        return {
            'flesch_reading_ease': flesch_reading_ease(text),
            'flesch_kincaid_grade': flesch_kincaid_grade(text),
            'word_count': len(text.split()),
            'sentence_count': len(sent_tokenize(text)),
            'avg_sentence_length': len(text.split()) / max(len(sent_tokenize(text)), 1),
            'difficulty_level': 'easy' if flesch_reading_ease(text) > 70 else 'medium' if flesch_reading_ease(text) > 30 else 'hard'
        }

class IntentClassifier:
    def __init__(self):
        self.intent_patterns = {
            'explanation': ['explain', 'what is', 'how does', 'why', 'describe', 'tell me about'],
            'example': ['example', 'instance', 'case', 'sample', 'demonstrate'],
            'summary': ['summarize', 'summary', 'overview', 'brief', 'main points'],
            'definition': ['define', 'definition', 'meaning', 'what does', 'means'],
            'comparison': ['compare', 'difference', 'versus', 'vs', 'contrast'],
            'application': ['how to', 'apply', 'use', 'implement', 'practice'],
            'clarification': ['clarify', 'confused', 'unclear', 'don\'t understand']
        }
    
    def classify_intent(self, message: str) -> Dict[str, Any]:
        """Classify user intent"""
        message_lower = message.lower()
        intent_scores = {}
        
        for intent, patterns in self.intent_patterns.items():
            score = sum(1 for pattern in patterns if pattern in message_lower)
            if score > 0:
                intent_scores[intent] = score
        
        if intent_scores:
            primary_intent = max(intent_scores, key=intent_scores.get)
            confidence = intent_scores[primary_intent] / len(message.split())
        else:
            primary_intent = 'general'
            confidence = 0.5
        
        return {
            'intent': primary_intent,
            'confidence': confidence,
            'all_intents': intent_scores
        }

class ConversationManager:
    def __init__(self):
        self.conversations = defaultdict(list)
        self.user_profiles = defaultdict(dict)
    
    def add_message(self, user_id: str, message: str, response: str, intent: str):
        """Add message to conversation history"""
        self.conversations[user_id].append({
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'response': response,
            'intent': intent
        })
        
        # Keep only last 20 messages
        if len(self.conversations[user_id]) > 20:
            self.conversations[user_id] = self.conversations[user_id][-20:]
    
    def get_context(self, user_id: str, last_n: int = 3) -> str:
        """Get recent conversation context"""
        if user_id not in self.conversations:
            return ""
        
        recent = self.conversations[user_id][-last_n:]
        context = []
        for msg in recent:
            context.append(f"Student: {msg['message']}")
            context.append(f"Assistant: {msg['response']}")
        
        return "\n".join(context)
    
    def update_user_profile(self, user_id: str, learning_data: Dict):
        """Update user learning profile"""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {
                'preferred_complexity': 'medium',
                'learning_style': 'balanced',
                'frequent_intents': [],
                'difficulty_preference': 'medium'
            }
        
        self.user_profiles[user_id].update(learning_data)

class AdaptiveExplainer:
    def __init__(self):
        self.complexity_levels = {
            'simple': "Explain in very simple terms, like to a beginner. Use everyday language and basic concepts.",
            'medium': "Provide a balanced explanation with some technical terms but keep it accessible.",
            'advanced': "Use technical language and assume prior knowledge. Include detailed concepts."
        }
    
    def generate_adaptive_explanation(self, content: str, topic: str, complexity: str = 'medium', intent: str = 'explanation') -> str:
        """Generate explanation adapted to complexity level and intent"""
        
        complexity_prompt = self.complexity_levels.get(complexity, self.complexity_levels['medium'])
        
        intent_prompts = {
            'explanation': "Provide a clear explanation of",
            'example': "Give practical examples of",
            'summary': "Summarize the key points about",
            'definition': "Define and explain",
            'comparison': "Compare and contrast",
            'application': "Explain how to apply"
        }
        
        intent_prompt = intent_prompts.get(intent, intent_prompts['explanation'])
        
        prompt = f"""{complexity_prompt}

{intent_prompt} "{topic}" based on this content:

{content[:1500]}

Focus on the specific request and adapt the explanation to the complexity level."""
        
        try:
            response = ollama.chat(
                model="mistral",
                messages=[{"role": "user", "content": prompt}]
            )
            return response["message"]["content"]
        except Exception as e:
            logger.error(f"Adaptive explanation error: {e}")
            return f"Here's what I found about {topic}: {content[:300]}..."

class LearningAnalytics:
    def __init__(self):
        self.user_analytics = defaultdict(lambda: {
            'total_questions': 0,
            'intent_distribution': defaultdict(int),
            'topic_interests': defaultdict(int),
            'difficulty_requests': defaultdict(int),
            'engagement_score': 0.0,
            'knowledge_gaps': [],
            'learning_progress': []
        })
    
    def track_interaction(self, user_id: str, intent: str, topic: str, difficulty: str, satisfaction: float = 0.5):
        """Track user interaction for analytics"""
        analytics = self.user_analytics[user_id]
        
        analytics['total_questions'] += 1
        analytics['intent_distribution'][intent] += 1
        analytics['topic_interests'][topic] += 1
        analytics['difficulty_requests'][difficulty] += 1
        
        # Update engagement score (moving average)
        analytics['engagement_score'] = (analytics['engagement_score'] * 0.8) + (satisfaction * 0.2)
        
        # Track learning progress
        analytics['learning_progress'].append({
            'timestamp': datetime.now().isoformat(),
            'topic': topic,
            'intent': intent,
            'difficulty': difficulty,
            'satisfaction': satisfaction
        })
    
    def detect_knowledge_gaps(self, user_id: str) -> List[str]:
        """Detect potential knowledge gaps"""
        analytics = self.user_analytics[user_id]
        gaps = []
        
        # Topics with many clarification requests
        for topic, count in analytics['topic_interests'].items():
            clarification_ratio = analytics['intent_distribution'].get('clarification', 0) / max(count, 1)
            if clarification_ratio > 0.3:
                gaps.append(f"Difficulty understanding {topic}")
        
        return gaps
    
    def get_learning_insights(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive learning insights"""
        analytics = self.user_analytics[user_id]
        
        return {
            'total_interactions': analytics['total_questions'],
            'most_common_intent': max(analytics['intent_distribution'], key=analytics['intent_distribution'].get) if analytics['intent_distribution'] else 'none',
            'favorite_topics': sorted(analytics['topic_interests'].items(), key=lambda x: x[1], reverse=True)[:5],
            'preferred_difficulty': max(analytics['difficulty_requests'], key=analytics['difficulty_requests'].get) if analytics['difficulty_requests'] else 'medium',
            'engagement_score': analytics['engagement_score'],
            'knowledge_gaps': self.detect_knowledge_gaps(user_id),
            'learning_trend': 'improving' if len(analytics['learning_progress']) > 5 and analytics['learning_progress'][-1]['satisfaction'] > analytics['learning_progress'][-5]['satisfaction'] else 'stable'
        }

class EnhancedRAGChatbot:
    def __init__(self):
        self.embedder = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        self.content_analyzer = ContentAnalyzer()
        self.intent_classifier = IntentClassifier()
        self.conversation_manager = ConversationManager()
        self.adaptive_explainer = AdaptiveExplainer()
        self.learning_analytics = LearningAnalytics()
        
        self.current_lesson = None
        self.chunks = []
        self.embeddings = None
        self.index = None
        self.lesson_metadata = {}
    
    def load_lesson(self, lesson_data: Dict[str, Any]):
        """Load lesson with enhanced analysis"""
        self.current_lesson = lesson_data
        content = lesson_data['content']
        
        # Analyze content
        self.lesson_metadata = {
            'sentiment': self.content_analyzer.analyze_sentiment(content),
            'difficulty': self.content_analyzer.assess_difficulty(content),
            'keywords': self.content_analyzer.extract_keywords(content),
            'entities': self.content_analyzer.extract_entities(content),
            'topics': self.content_analyzer.extract_topics([content]) if len(content) > 100 else []
        }
        
        # Create semantic chunks
        self.chunks = self.create_semantic_chunks(content)
        
        # Create embeddings
        self.embeddings = self.embedder.encode(self.chunks, convert_to_numpy=True)
        
        # Setup FAISS index
        dimension = self.embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(self.embeddings)
    
    def create_semantic_chunks(self, content: str) -> List[str]:
        """Create semantically coherent chunks"""
        sentences = sent_tokenize(content)
        chunks = []
        current_chunk = []
        current_word_count = 0
        
        for sentence in sentences:
            words_in_sentence = len(sentence.split())
            if current_word_count + words_in_sentence > 200 and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_word_count = words_in_sentence
            else:
                current_chunk.append(sentence)
                current_word_count += words_in_sentence
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def semantic_search(self, query: str, k: int = 3) -> List[str]:
        """Enhanced semantic search"""
        if not self.index:
            return []
        
        # Expand query with synonyms and related terms
        expanded_query = self.expand_query(query)
        
        q_emb = self.embedder.encode([expanded_query], convert_to_numpy=True)
        D, I = self.index.search(q_emb, k=k)
        
        valid_indices = [i for i in I[0] if 0 <= i < len(self.chunks)]
        return [self.chunks[i] for i in valid_indices]
    
    def expand_query(self, query: str) -> str:
        """Expand query with related terms"""
        # Simple expansion using keywords from lesson
        query_words = set(query.lower().split())
        related_keywords = []
        
        for kw in self.lesson_metadata.get('keywords', [])[:5]:
            if any(word in kw['keyword'] for word in query_words):
                related_keywords.append(kw['keyword'])
        
        return query + " " + " ".join(related_keywords)
    
    def chat(self, user_message: str, user_id: str = "default") -> str:
        """Enhanced chat with context awareness and personalization"""
        if not self.current_lesson:
            return "No lesson loaded."
        
        # Quick greeting detection
        greetings = ['hi', 'hello', 'hey', 'hiii', 'hii', 'good morning', 'good afternoon', 'good evening']
        if user_message.lower().strip() in greetings or len(user_message.strip()) <= 5:
            lesson_title = self.current_lesson.get('title', 'this lesson')
            return f"Hello! I'm here to help you learn about {lesson_title}. What would you like to know?"
        
        # Classify intent
        intent_data = self.intent_classifier.classify_intent(user_message)
        intent = intent_data['intent']
        
        # Get conversation context
        context = self.conversation_manager.get_context(user_id)
        
        # Semantic search with context
        relevant_chunks = self.semantic_search(user_message + " " + context)
        
        if not relevant_chunks:
            return "Could not find relevant information in the lesson."
        
        context_text = "\n\n".join(relevant_chunks)
        
        # Get user profile for personalization
        user_profile = self.conversation_manager.user_profiles.get(user_id, {})
        complexity = user_profile.get('preferred_complexity', 'medium')
        
        # Generate adaptive response
        if intent in ['explanation', 'example', 'summary', 'definition', 'comparison', 'application']:
            response = self.adaptive_explainer.generate_adaptive_explanation(
                context_text, user_message, complexity, intent
            )
        else:
            # Standard RAG response
            response = self.generate_standard_response(user_message, context_text, context)
        
        # Track interaction
        self.learning_analytics.track_interaction(user_id, intent, user_message[:50], complexity)
        
        # Update conversation history
        self.conversation_manager.add_message(user_id, user_message, response, intent)
        
        return response
    
    def generate_standard_response(self, user_message: str, context_text: str, conversation_context: str) -> str:
        """Generate standard RAG response with context"""
        prompt = f"""Answer briefly based on this content:

{context_text[:800]}

Question: {user_message}

Give a concise, helpful answer."""
        
        try:
            response = ollama.chat(
                model="mistral",
                messages=[{"role": "user", "content": prompt}],
                options={
                    "temperature": 0.1,
                    "num_predict": 150,
                    "top_p": 0.9
                }
            )
            return response["message"]["content"]
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return f"Based on the lesson content: {context_text[:500]}..."
    
    def get_lesson_insights(self) -> Dict[str, Any]:
        """Get insights about the current lesson"""
        return self.lesson_metadata
    
    def get_user_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get user learning analytics"""
        return self.learning_analytics.get_learning_insights(user_id)

# Legacy compatibility
class LessonProcessor:
    def __init__(self):
        self._transcriber = None
        self._youtube_dl = None
    
    @property
    def transcriber(self):
        if self._transcriber is None:
            from transcriber import FastVideoTranscriber
            self._transcriber = FastVideoTranscriber(
                model_size="tiny",  # Fastest model
                device="auto",      # Use GPU if available
                compute_type="int8", # Fastest compute type
                num_workers=4       # More workers for parallel processing
            )
        return self._transcriber
    
    @property
    def youtube_dl(self):
        if self._youtube_dl is None:
            import yt_dlp
            self._youtube_dl = yt_dlp
        return self._youtube_dl
    
    def process_text_file(self, content: str, filename: str) -> Dict[str, Any]:
        return {
            'type': 'text',
            'title': filename,
            'content': content,
            'processed_at': datetime.now().isoformat()
        }
    
    def process_pdf(self, file_path: str, filename: str) -> Dict[str, Any]:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text_parts = []
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text.strip():
                    text_parts.append(page_text)
        
        return {
            'type': 'pdf',
            'title': filename,
            'content': '\n'.join(text_parts),
            'processed_at': datetime.now().isoformat()
        }
    
    def process_docx(self, file_path: str, filename: str) -> Dict[str, Any]:
        doc = docx.Document(file_path)
        text_parts = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text)
        
        return {
            'type': 'docx',
            'title': filename,
            'content': '\n'.join(text_parts),
            'processed_at': datetime.now().isoformat()
        }
    
    def process_video(self, file_path: str, filename: str) -> Dict[str, Any]:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            output_path = tmp.name
        
        # Use fastest transcription settings
        result_path = self._fast_transcribe_video(
            video_path=file_path,
            output_path=output_path
        )
        
        with open(result_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if os.path.exists(result_path):
            os.unlink(result_path)
        
        return {
            'type': 'video',
            'title': filename,
            'content': content,
            'processed_at': datetime.now().isoformat()
        }
    
    def _fast_transcribe_video(self, video_path: str, output_path: str) -> str:
        """Ultra-fast video transcription with optimized settings"""
        # Create temporary audio file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
            temp_audio_path = temp_audio.name
        
        try:
            # Extract audio
            if not self.transcriber.extract_audio(video_path, temp_audio_path):
                raise Exception("Failed to extract audio from video")
            
            # Ultra-fast transcription with minimal parameters
            result = self.transcriber.transcribe_audio(
                temp_audio_path,
                task="translate",
                beam_size=1,  # Fastest beam size
                best_of=1,    # No sampling
                temperature=0.0,  # Deterministic
                word_timestamps=False,  # Skip word timestamps
                condition_on_previous_text=False  # Skip context
            )
            
            if "error" in result:
                raise Exception(f"Transcription failed: {result['error']}")
            
            # Save only the text
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result["full_text"])
            
            return output_path
            
        finally:
            # Clean up temporary audio file
            if os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
    
    def process_youtube_url(self, url: str) -> Dict[str, Any]:
        url = url.strip()
        if 'youtu.be/' in url:
            video_id = url.split('youtu.be/')[-1].split('?')[0]
            url = f"https://www.youtube.com/watch?v={video_id}"
        
        ydl_opts_info = {'quiet': True, 'no_warnings': True}
        with self.youtube_dl.YoutubeDL(ydl_opts_info) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'YouTube Video')
            duration = info.get('duration', 0)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(temp_dir, 'video.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
            }
            
            with self.youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            downloaded_files = list(Path(temp_dir).glob('video.*'))
            if not downloaded_files:
                raise Exception("Download failed")
            
            video_file = downloaded_files[0]
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
                output_path = tmp.name
            
            result_path = self._fast_transcribe_video(
                video_path=str(video_file),
                output_path=output_path
            )
            
            with open(result_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if os.path.exists(result_path):
                os.unlink(result_path)
        
        return {
            'type': 'youtube',
            'title': title,
            'content': content,
            'url': url,
            'duration': duration,
            'processed_at': datetime.now().isoformat()
        }

# Aliases for backward compatibility
RAGChatbot = EnhancedRAGChatbot

class QuizGenerator:
    def generate_quiz(self, content: str, num_questions: int = 5, difficulty: str = "medium") -> List[Dict]:
        words = content.lower().split()
        stop_words = {'the', 'is', 'at', 'which', 'on', 'and', 'a', 'to', 'are', 'as', 'was', 'were', 'been', 'be'}
        keywords = [word for word in words if len(word) > 3 and word not in stop_words]
        top_keywords = list(set(keywords))[:10]
        
        quiz_prompt = f"""Generate exactly {num_questions} quiz questions based on this content with {difficulty} difficulty.

CONTENT: {content[:2500]}

KEY TOPICS: {', '.join(top_keywords)}

Return a JSON array of questions in this exact format:
[
  {{
    "question": "Question text here?",
    "type": "multiple_choice",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_answer": "Option A",
    "explanation": "Why this is correct"
  }}
]

Make questions {difficulty} difficulty level. Mix multiple choice and true/false questions."""

        try:
            response = ollama.chat(
                model="mistral",
                messages=[{"role": "user", "content": quiz_prompt}]
            )
            
            response_text = response["message"]["content"]
            
            # Extract JSON from response
            import re
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                questions_json = json_match.group()
                questions = json.loads(questions_json)
                return questions[:num_questions]
            else:
                return self._generate_fallback_questions(content, num_questions)
                
        except Exception as e:
            logger.error(f"Quiz generation error: {e}")
            return self._generate_fallback_questions(content, num_questions)
    
    def _generate_fallback_questions(self, content: str, num_questions: int) -> List[Dict]:
        """Generate simple fallback questions"""
        sentences = sent_tokenize(content)[:num_questions]
        questions = []
        
        for i, sentence in enumerate(sentences):
            if len(sentence.split()) > 5:
                questions.append({
                    "question": f"What does this statement refer to: '{sentence[:100]}...'?",
                    "type": "multiple_choice",
                    "options": ["Concept A", "Concept B", "Concept C", "Concept D"],
                    "correct_answer": "Concept A",
                    "explanation": "Based on the lesson content."
                })
        
        return questions
    
    def evaluate_answer(self, question: Dict, user_answer: Any) -> Dict[str, Any]:
        """Evaluate user answer"""
        correct_answer = question.get('correct_answer')
        
        if question.get('type') == 'true_false':
            is_correct = user_answer == correct_answer
        else:
            is_correct = str(user_answer).strip() == str(correct_answer).strip()
        
        return {
            'correct': is_correct,
            'correct_answer': correct_answer,
            'explanation': question.get('explanation', 'No explanation available.')
        }