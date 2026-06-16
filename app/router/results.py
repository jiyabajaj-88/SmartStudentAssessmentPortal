from fastapi import APIRouter, Depends
from app.services.results_service import get_student_results, get_results_by_assessment
from dependencies import get_current_student

router = APIRouter()

@router.get("/results")
def get_results(
    current_student = Depends(get_current_student)
):
    return get_student_results(
        current_student["student_id"]
    )

@router.get("/results/assessment/{assessment_id}")
def get_result(
    assessment_id: int,
    current_student = Depends(get_current_student)
):
    return get_results_by_assessment(
        current_student["student_id"],
        assessment_id
    )