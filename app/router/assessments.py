from fastapi import APIRouter, Depends
from app.services.assessment_service import get_assessments_by_class, get_assessment_by_id
from app.services.question_service import get_questions_by_assessment, get_question_by_id
from dependencies import get_current_student

router = APIRouter()

@router.get("/assessments")
def get_assessments(
    current_student = Depends(get_current_student)
):

    return get_assessments_by_class(
        current_student["student_class"]
    )

@router.get("/assessments/{assessment_id}")
def get_assessment(assessment_id: int):
    return get_assessment_by_id(assessment_id)

@router.get("/assessments/{assessment_id}/questions")
def get_questions(assessment_id: int):
    return get_questions_by_assessment(assessment_id)

@router.get("/questions/{question_id}")
def get_question(question_id: int):
    return get_question_by_id(question_id)
