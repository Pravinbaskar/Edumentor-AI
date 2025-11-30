# EduMentor AI

Multi-agent, tool-augmented tutoring backend with FAISS vector database + Streamlit UI using the latest OpenAI Python SDK.

## Features

- 🎓 **Personalized Learning**: Student profiles with grade, subject preferences, and proficiency levels
- 📚 **Vector Database**: Upload subject-specific PDFs that are stored in FAISS for contextual retrieval
- 🤖 **Multi-Agent System**: Orchestrated tutor and planner agents with LangGraph support
- 📊 **Subject Management**: Separate vector stores for Maths, Science, and EVS
- 💬 **Context-Aware Responses**: Automatically retrieves relevant content from uploaded PDFs when answering questions
- 📜 **Chat History**: SQLite database stores all Q&A pairs with timestamps and subject tags
- 🔍 **History Panel**: Browse, filter, and reload past conversations from the right sidebar
- 📝 **Quiz System**: AI-generated quizzes with automatic grading and downloadable results
- 💾 **Quiz Results Database**: All quiz attempts stored in SQLite with detailed analytics

## Prerequisites

- Python 3.11+
- An OpenAI API key

## Local development

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=your_real_key_here  # or set in your shell
uvicorn edumentor.main:app --reload
```

If you added LangGraph support, install extras and run:

```bash
pip install -r requirements.txt
# ensure langgraph is installed (requirements.txt includes it)
export OPENAI_API_KEY=your_real_key_here
uvicorn edumentor.main:app --reload
```

Then in another terminal:

```bash
streamlit run streamlit_app.py
```

The API will be at http://localhost:8000 and the UI at http://localhost:8501.

## Vector Database Usage

### Upload PDFs for Subjects

1. Select a subject (maths, science, or evs) in the UI
2. Click "📚 Manage Documents"
3. Upload PDF files for that subject
4. PDFs are automatically:
   - Extracted and chunked
   - Embedded using sentence-transformers
   - Stored in FAISS vector database (per subject)

### How It Works

When a student asks a question:
1. System searches the selected subject's vector store
2. Top 3 most relevant document chunks are retrieved
3. Context is injected into the prompt
4. LLM answers using uploaded PDFs + general knowledge
5. If no relevant documents exist, LLM uses general knowledge

### API Endpoints

- `POST /upload-pdf/{subject}` - Upload PDF for subject
- `GET /subject-stats/{subject}` - Get document statistics
- `DELETE /subject-data/{subject}` - Clear all documents for subject

### Data Storage

- Vector indexes: `data/vector_store/{subject}_index.faiss`
- Metadata: `data/vector_store/{subject}_metadata.json`
- Chat history: `data/chat_history.db` (SQLite database)
- Quiz results: `data/quiz_results.db` (SQLite database)
- Student profiles: `data/profiles.json`

## Chat History Database

### Features
- **Automatic Saving**: Every Q&A pair is automatically saved to SQLite database
- **Persistent Storage**: History survives app restarts
- **Filter by Subject**: View history for specific subjects (maths, science, evs)
- **Search & Browse**: Access past conversations from the history panel
- **Statistics**: Track total questions, sessions, and questions per subject

### API Endpoints

- `GET /chat-history/{user_id}` - Get user's chat history (with optional subject filter)
- `GET /chat-history/{user_id}/sessions` - Get recent chat sessions
- `GET /chat-history/{user_id}/stats` - Get chat statistics
- `DELETE /chat-history/{user_id}` - Clear all history for user

### Database Schema

```sql
CREATE TABLE chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    subject TEXT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT
)
```

## Quiz System

### Features
- **AI-Generated Questions**: Create custom quizzes on any topic using GPT-4
- **Multiple Choice**: 4 options per question with detailed explanations
- **Adaptive Difficulty**: Choose beginner, intermediate, or advanced levels
- **Instant Grading**: Automatic scoring with correct/incorrect feedback
- **Downloadable Results**: Export quiz results as text files
- **Performance Tracking**: View statistics across all quiz attempts
- **Subject-Based**: Quizzes aligned with selected subject (maths, science, evs)

### How to Use

1. **Start a Quiz**:
   - Select subject from dropdown
   - Enter topic (e.g., "Algebra", "Photosynthesis")
   - Choose difficulty level
   - Select number of questions (3-10)
   - Click "Start Quiz"

2. **Take Quiz**:
   - Answer all multiple choice questions
   - Click "Submit Quiz" when done

3. **View Results**:
   - See score percentage and pass/fail status
   - Review detailed explanations for each question
   - Download results as text file
   - View overall quiz statistics

### API Endpoints

- `POST /quiz/generate` - Generate new quiz
- `POST /quiz/submit` - Submit answers and get results
- `GET /quiz/results/{user_id}` - Get quiz history
- `GET /quiz/result/{result_id}` - Get detailed result
- `GET /quiz/statistics/{user_id}` - Get performance statistics
- `DELETE /quiz/results/{user_id}` - Clear all quiz results

### Database Schema

```sql
CREATE TABLE quiz_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    topic TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    total_questions INTEGER NOT NULL,
    correct_answers INTEGER NOT NULL,
    score_percentage REAL NOT NULL,
    questions_data TEXT NOT NULL,
    user_answers TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    time_taken_seconds INTEGER
)
```

## Docker (backend only)

```bash
docker build -t edumentor-backend .
docker run -p 8000:8000 -e OPENAI_API_KEY=your_real_key edumentor-backend
```

## Docker Compose (backend + UI)

```bash
cp .env.example .env
# edit .env and set OPENAI_API_KEY
docker compose up --build
```

This will start:
- API at http://localhost:8000
- UI at http://localhost:8501
