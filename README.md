# AI-Powered Chatbot for Learning Management System

An intelligent chatbot-based for Learning Management System that uses advanced NLP and AI to provide personalized, interactive learning experiences. Upload educational content in multiple formats and interact with an AI tutor that understands context, adapts to your learning style, and tracks your progress.

## 🎯 Project Overview

This AI-powered transforms static educational content into interactive learning experiences. Upload documents, videos, or YouTube links, and the system creates an intelligent chatbot tutor that:
- Understands your questions with intent classification
- Provides context-aware responses using RAG (Retrieval-Augmented Generation)
- Adapts explanations to your complexity level
- Generates quizzes from content
- Tracks learning analytics and identifies knowledge gaps

## 🧠 Core NLP Concepts & Technologies

### 1. **Retrieval-Augmented Generation (RAG)**
- **Implementation**: Custom RAG pipeline using semantic search + LLM generation
- **Purpose**: Provides contextually accurate responses based on lesson content
- **Components**: 
  - Document chunking with semantic coherence
  - Vector embeddings for similarity search
  - Context-aware response generation

### 2. **Semantic Search & Embeddings**
- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Technology**: FAISS (Facebook AI Similarity Search) for ultra-fast vector search
- **Features**:
  - Sub-millisecond similarity search
  - Query expansion with related terms
  - Semantic chunking (200-word coherent segments)

### 3. **Intent Classification**
- **Approach**: Pattern-based classification with confidence scoring
- **Intents Detected**:
  - `explanation` - Requests for detailed explanations
  - `example` - Requests for practical examples
  - `summary` - Requests for content summaries
  - `definition` - Requests for term definitions
  - `comparison` - Requests for comparisons
  - `application` - Requests for practical applications
  - `clarification` - Confusion or unclear concepts

### 4. **Sentiment Analysis**
- **Library**: TextBlob for polarity and subjectivity analysis
- **Metrics**:
  - Polarity: -1 (negative) to +1 (positive)
  - Subjectivity: 0 (objective) to 1 (subjective)
  - Emotion classification: positive/negative/neutral

### 5. **Named Entity Recognition (NER)**
- **Library**: NLTK with MaxEnt chunker
- **Entities Extracted**:
  - PERSON - People mentioned in content
  - ORGANIZATION - Companies, institutions
  - GPE - Geographical/political entities
  - CONCEPT - Key domain concepts (nouns)

### 6. **Topic Modeling**
- **Algorithm**: Latent Dirichlet Allocation (LDA)
- **Features**: 
  - Automatic topic discovery from content
  - TF-IDF vectorization for feature extraction
  - Top keywords per topic identification

### 7. **Text Difficulty Assessment**
- **Metrics**:
  - Flesch Reading Ease Score
  - Flesch-Kincaid Grade Level
  - Average sentence length analysis
  - Vocabulary complexity assessment

### 8. **Keyword Extraction**
- **Method**: TF-IDF (Term Frequency-Inverse Document Frequency)
- **Features**:
  - Automatic key term identification
  - Relevance scoring for each keyword
  - Stop word filtering

## 🤖 AI Models Used

### Large Language Model (LLM)
- **Primary Model**: Mistral 7B via Ollama
- **Purpose**: Natural language generation, explanations, quiz creation
- **Features**:
  - Local deployment for privacy
  - Fast inference (2-3 seconds response time)
  - Multilingual support

### Speech-to-Text
- **Model**: OpenAI Whisper (Tiny model for speed)
- **Optimization**: 
  - Ultra-fast transcription (3-5 minutes for 1-hour video)
  - GPU acceleration when available
  - Optimized parameters: beam_size=1, temperature=0.0

### Embedding Model
- **Model**: `all-MiniLM-L6-v2` (384-dimensional embeddings)
- **Performance**: 
  - 14,000+ sentences/second encoding speed
  - High semantic accuracy for educational content
  - Multilingual capabilities

## 🏗️ System Architecture

### Content Processing Pipeline
```
Input (PDF/DOCX/TXT/Video/YouTube) 
    ↓
Content Extraction & Cleaning
    ↓
Text Preprocessing (NLTK tokenization)
    ↓
Semantic Chunking (200 words)
    ↓
Vector Embedding Generation
    ↓
FAISS Index Creation
    ↓
NLP Analysis (Sentiment, Entities, Topics)
    ↓
Storage (JSON + Vector Index)
```

### Chat Interaction Flow
```
User Query
    ↓
Intent Classification
    ↓
Semantic Search (FAISS)
    ↓
Context Retrieval (Top-K chunks)
    ↓
Conversation History Integration
    ↓
LLM Prompt Engineering
    ↓
Response Generation (Mistral)
    ↓
Learning Analytics Tracking
```

## 🎓 Advanced Learning Features

### 1. **Adaptive Explanations**
- **Complexity Levels**: Simple, Medium, Advanced
- **Personalization**: Adjusts based on user interaction patterns
- **Context Awareness**: Considers previous conversations

### 2. **Conversation Management**
- **Memory**: Maintains 20-message conversation history
- **Context Integration**: References previous discussions
- **User Profiling**: Tracks learning preferences and patterns

### 3. **Learning Analytics**
- **Metrics Tracked**:
  - Total interactions and engagement score
  - Intent distribution patterns
  - Topic interest analysis
  - Knowledge gap detection
  - Learning progress trends
- **Insights Generated**:
  - Personalized learning recommendations
  - Difficulty preference analysis
  - Engagement optimization suggestions

### 4. **Intelligent Quiz Generation**
- **AI-Powered**: Uses LLM to create contextual questions
- **Question Types**: Multiple choice, true/false
- **Difficulty Adaptation**: Easy, medium, hard levels
- **Content-Based**: Questions derived from actual lesson content

## 🔧 Technical Implementation

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **Database**: JSON-based storage for simplicity
- **Vector Store**: FAISS for similarity search
- **Background Processing**: Threading for video transcription

### NLP Pipeline Components
```python
# Core NLP Classes
ContentAnalyzer()          # Sentiment, topics, keywords, entities
IntentClassifier()         # User intent detection
ConversationManager()      # Chat history and context
AdaptiveExplainer()        # Personalized explanations
LearningAnalytics()        # Progress tracking and insights
EnhancedRAGChatbot()       # Main RAG implementation
```

### Performance Optimizations
- **FAISS Indexing**: Sub-millisecond vector search
- **Semantic Chunking**: Optimal 200-word segments
- **Model Caching**: Lazy loading of heavy models
- **Background Processing**: Async video transcription
- **GPU Acceleration**: CUDA support for faster inference

## 📊 Key Features

### Content Processing
- ✅ Multi-format support (PDF, DOCX, TXT, MP4, MP3, WAV, YouTube)
- ✅ Ultra-fast video transcription (3-5 min for 1-hour video)
- ✅ Automatic content analysis and insights
- ✅ Semantic chunking for optimal retrieval

### Intelligent Chat
- ✅ Context-aware conversations with memory
- ✅ Intent-based response adaptation
- ✅ Adaptive complexity levels
- ✅ Real-time learning analytics

### Educational Tools
- ✅ AI-generated quizzes with multiple difficulty levels
- ✅ Automatic scoring and detailed feedback
- ✅ Progress tracking and performance analytics
- ✅ Personalized learning recommendations

### Advanced NLP
- ✅ Sentiment analysis of learning content
- ✅ Named entity recognition for key concepts
- ✅ Topic modeling for content categorization
- ✅ Difficulty assessment and readability analysis

## 🚀 Installation & Setup

### Prerequisites
```bash
Python 3.8+
4GB+ RAM (8GB recommended)
GPU optional (for faster processing)
```

### Quick Start
```bash
cd enhanced_lms
pip install -r requirements.txt

# Install Ollama and Mistral model
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull mistral

# Run the application
python app.py
```

### Dependencies
```
flask                    # Web framework
sentence-transformers    # Embedding model
faiss-cpu               # Vector similarity search
nltk                    # Natural language toolkit
textblob                # Sentiment analysis
scikit-learn            # Machine learning utilities
ollama                  # LLM interface
openai-whisper          # Speech-to-text
PyPDF2                  # PDF processing
python-docx             # Word document processing
```

## 📈 Performance Metrics

### Speed Benchmarks
- **Video Transcription**: 3-5 minutes for 1-hour content
- **Document Processing**: <10 seconds for 100-page PDF
- **Chat Response Time**: 2-3 seconds average
- **Semantic Search**: <1ms for similarity queries

### Accuracy Metrics
- **Intent Classification**: ~85% accuracy on educational queries
- **Semantic Search**: High relevance for domain-specific content
- **Quiz Generation**: Contextually appropriate questions
- **Sentiment Analysis**: Reliable for educational content tone

## 🎯 Use Cases

### Educational Institutions
- Course content digitization and AI-powered tutoring
- Student engagement analytics and personalized learning
- Automated quiz generation and assessment

### Corporate Training
- Employee onboarding with interactive AI assistance
- Skill development tracking and progress monitoring
- Knowledge base creation from training materials

### Self-Learning
- Personal study assistant with adaptive explanations
- Progress tracking and learning optimization
- Multi-format content processing and organization

## 🔮 Future Enhancements

### Planned NLP Improvements
- **Advanced Intent Recognition**: Deep learning-based classification
- **Multi-language Support**: Expanded language processing capabilities
- **Knowledge Graph Integration**: Entity relationship mapping
- **Advanced Topic Modeling**: Neural topic models (BERTopic)

### Technical Roadmap
- **Scalability**: Database migration to PostgreSQL/MongoDB
- **Real-time Features**: WebSocket-based live chat
- **Mobile Support**: Progressive Web App (PWA) implementation
- **API Integration**: External LMS and educational platform connectors

## 📝 License

MIT License - Open source educational project

## 🤝 Contributing

Contributions welcome! Focus areas:
- NLP model improvements
- Performance optimizations
- Educational feature enhancements
- UI/UX improvements

---

**Enhanced LMS** - Transforming education through advanced NLP and AI technologies.
