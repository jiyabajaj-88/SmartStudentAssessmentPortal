from fastapi import APIRouter, Depends
from app.services.results_service import get_student_results, get_results_by_assessment
from app.dependencies import get_current_student
from app.schemas import ResultResponse
from typing import List
router = APIRouter()

@router.get("/results",response_model=List[ResultResponse])
def get_results(
    current_student = Depends(get_current_student)
):
    return get_student_results(
        current_student["student_id"]
    )

@router.get("/results/assessment/{assessment_id}",response_model=List[ResultResponse])
def get_result(
    assessment_id: int,
    current_student = Depends(get_current_student)
):
    return get_results_by_assessment(
        current_student["student_id"],
        assessment_id
    )