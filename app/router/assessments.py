from fastapi import APIRouter, Depends, HTTPException
from app.services.assessment_service import get_assessments_for_student, get_assessment_by_id
from app.services.question_service import get_questions_by_assessment, get_question_by_id
from dependencies import get_current_student
from typing import List
from app.schemas import AssessmentResponse, QuestionWithOptionsResponse

router = APIRouter()

@router.get("/assessments",response_model=List[AssessmentResponse])
def get_assessments(
    current_student = Depends(get_current_student)
):

    return get_assessments_for_student(
        current_student["student_class"]
    )

@router.get("/assessments/{assessment_id}",response_model=AssessmentResponse)
def get_assessment(assessment_id: int):
    return get_assessment_by_id(assessment_id)

@router.get("/assessments/{assessment_id}/questions", response_model=List[QuestionWithOptionsResponse])
def get_questions(assessment_id: int):
    return get_questions_by_assessment(assessment_id)

@router.get("/questions/{question_id}", response_model=QuestionWithOptionsResponse)
def get_question(question_id: int):
    question = get_question_by_id(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question
