"""
app/router/ai_practice.py

Thin router — validates requests, delegates to the service layer.
No Gemini calls, no prompts, no DB cursors here.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from app.dependencies import get_current_student
from app.services import ai_practice_service as svc

router = APIRouter(prefix="/ai", tags=["ai"])


# ── Request schemas ────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    topic: str
    subject: str


class AnswerSubmit(BaseModel):
    practice_question_id: int
    answer_text: Optional[str] = None           # subjective
    selected_option_text: Optional[str] = None  # objective


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/practice/generate")
def generate_practice(
    payload: GenerateRequest,
    current_student=Depends(get_current_student),
):
    return svc.generate_assessment(
        student_id=current_student["student_id"],
        student_class=current_student["student_class"],
        subject=payload.subject.strip(),
        topic=payload.topic.strip(),
    )


@router.get("/practice")
def list_practice(current_student=Depends(get_current_student)):
    return svc.list_assessments(current_student["student_id"])


@router.get("/practice/{practice_assessment_id}")
def get_practice(
    practice_assessment_id: int,
    current_student=Depends(get_current_student),
):
    return svc.get_assessment(practice_assessment_id, current_student["student_id"])


@router.post("/practice/{practice_assessment_id}/submit")
def submit_answers(
    practice_assessment_id: int,
    answers: list[AnswerSubmit],
    current_student=Depends(get_current_student),
):
    return svc.save_answers(
        practice_assessment_id,
        current_student["student_id"],
        [a.model_dump() for a in answers],
    )


@router.post("/practice/{practice_assessment_id}/evaluate")
def evaluate_practice(
    practice_assessment_id: int,
    current_student=Depends(get_current_student),
):
    return svc.evaluate_submission(practice_assessment_id, current_student["student_id"])


@router.get("/practice/{practice_assessment_id}/result")
def get_result(
    practice_assessment_id: int,
    current_student=Depends(get_current_student),
):
    return svc.get_result(practice_assessment_id, current_student["student_id"])