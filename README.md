# EduMentor AI

Multi-agent, tool-augmented tutoring backend + Streamlit UI using the latest OpenAI Python SDK.

## Prerequisites

- Python 3.11+
- An OpenAI API key

## Local development

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=your_real_key_here  # or set in your shell
uvicorn edumentor.main:app --reload
```

Then in another terminal:

```bash
streamlit run streamlit_app.py
```

The API will be at http://localhost:8000 and the UI at http://localhost:8501.

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
