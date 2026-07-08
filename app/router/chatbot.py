
import os
from google import genai

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.dependencies import get_current_student
from app.retrieval import retrieve, retrieve_for_weak_topics
from dotenv import load_dotenv

load_dotenv()

_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash"]

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])

NO_CONTEXT_THRESHOLD = 0.6


# ---------- SCHEMAS ----------
class AskRequest(BaseModel):
    question: str
    subject: Optional[str] = None


class AskResponse(BaseModel):
    answer: str
    sources: list


class WeakTopic(BaseModel):
    topic: str
    subject: str
    score: float


class WeakTopicsResponse(BaseModel):
    weak_topics: list[WeakTopic]


class ReviseRequest(BaseModel):
    topic_name: str       # revise one specific topic at a time
    subject: Optional[str] = None


class ReviseResponse(BaseModel):
    topic: str
    revision_content: str


# ---------- HELPERS ----------
def build_context(chunks):
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(
            f"[Source {i} — {chunk['subject']}: {chunk['topic']}]\n{chunk['chunk_text']}"
        )
    return "\n\n".join(parts)


def call_gemini(prompt: str) -> str:
    for model in _MODELS:
        try:
            response = _client.models.generate_content(model=model, contents=prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Gemini error ({model}): {e}")  # add this line
            continue
    raise HTTPException(status_code=502, detail="Gemini API unavailable. Please try again.")


# ---------- FLOW A: DOUBT CLEARING ----------
@router.post("/ask", response_model=AskResponse)
def ask(request: AskRequest, current_student=Depends(get_current_student)):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    chunks = retrieve(query=question, top_k=5, subject=request.subject or None)
    strong_chunks = [c for c in chunks if c["distance"] < NO_CONTEXT_THRESHOLD]

    if not strong_chunks:
        return AskResponse(
            answer=(
                "I couldn't find relevant information in the syllabus for your question. "
                "Try rephrasing, or check if it's within the Class 12 syllabus."
            ),
            sources=[]
        )

    context = build_context(strong_chunks)
    prompt = f"""You are a helpful and friendly study assistant for Class 12 students.
Answer the student's question using ONLY the syllabus content provided below.
If the answer is not fully covered in the content, say so honestly and answer as best you can.
Keep your answer clear, concise, and student-friendly. Use simple language and examples where helpful.

--- SYLLABUS CONTENT ---
{context}

--- STUDENT QUESTION ---
{question}

Answer:"""

    answer = call_gemini(prompt)

    seen = set()
    unique_sources = []
    for c in strong_chunks:
        key = (c["subject"], c["topic"])
        if key not in seen:
            seen.add(key)
            unique_sources.append({"subject": c["subject"], "topic": c["topic"]})

    return AskResponse(answer=answer, sources=unique_sources)


# ---------- GET WEAK TOPICS (list only, no generation) ----------
@router.get("/weak-topics", response_model=WeakTopicsResponse)
def get_weak_topics(current_student=Depends(get_current_student)):
    """
    Returns the student's weak topics list without generating any content.
    Used by the frontend to show topic selection UI.
    """
    import psycopg2
    from psycopg2.extras import RealDictCursor
    import os

    conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT t.name as topic, t.subject, swt.score
            FROM student_weak_topics swt
            JOIN topics t ON swt.topic_id = t.topic_id
            WHERE swt.student_id = %s
            ORDER BY swt.score ASC
        """, (current_student["student_id"],))
        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No weak topics found.")

    return WeakTopicsResponse(
        weak_topics=[
            WeakTopic(topic=r["topic"], subject=r["subject"], score=float(r["score"]))
            for r in rows
        ]
    )


# ---------- FLOW B: REVISION FOR ONE TOPIC ----------
@router.post("/revise", response_model=ReviseResponse)
def revise(request: ReviseRequest, current_student=Depends(get_current_student)):
    """
    Generates revision content for ONE specific topic.
    Frontend calls this after the student picks a topic from the list.
    """
    topic_name = request.topic_name.strip()
    subject = request.subject or None

    chunks = retrieve(
        query=topic_name,
        top_k=5,
        subject=subject,
        topic_names=[topic_name]
    )

    if not chunks:
        raise HTTPException(
            status_code=404,
            detail=f"No syllabus content found for topic '{topic_name}'."
        )

    context = build_context(chunks)

    prompt = f"""You are a helpful and friendly study assistant for Class 12 students.
A student needs to revise the topic: {topic_name} ({subject or 'General'})

Using ONLY the syllabus content provided below, generate a focused revision summary.
Structure your response as:
1. Core concept — brief, clear explanation
2. Key points to remember — bullet points of the most important ideas
3. Quick example — one simple example if relevant

Keep the language simple and encouraging. Address the student directly.

--- SYLLABUS CONTENT ---
{context}

Revision Summary:"""

    revision_content = call_gemini(prompt)

    return ReviseResponse(topic=topic_name, revision_content=revision_content)