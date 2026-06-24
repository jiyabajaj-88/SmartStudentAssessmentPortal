from fastapi import APIRouter, Depends, HTTPException
from app.services.submission_service import create_submission, get_submission_by_id, get_submissions_by_student
from app.services.evaluation_service import evaluate_submission
from app.dependencies import get_current_student
from app.services.answers_service import get_answers_by_submission
from typing import List
from app.schemas import SubmittedAnswerResponse,SubmissionResponse,ResultResponse
router = APIRouter()

@router.get("/submissions", response_model=List[SubmissionResponse])
def list_submissions(current_student = Depends(get_current_student)):
    return get_submissions_by_student(current_student["student_id"])

@router.get("/submissions/{submission_id}/answers",response_model=List[SubmittedAnswerResponse])
def get_answers(submission_id: int, current_student = Depends(get_current_student)):
    submission = get_submission_by_id(submission_id)
    if not submission:
        raise HTTPException(
            status_code=404, 
            detail="Error 404: Submission not found"
            )
    
    if submission["student_id"] != current_student["student_id"]:
        raise HTTPException(
            status_code=403, 
            detail="Error 403: You are not authorized to view answers for this submission"
            )
    
    return get_answers_by_submission(submission_id)


@router.post("/submissions",response_model=SubmissionResponse)
def create_submission_api(
    assessment_id: int,
    current_student = Depends(get_current_student)
):
    return create_submission(
        current_student["student_id"],
        assessment_id
    )


@router.post("/submissions/{submission_id}/evaluate",response_model=ResultResponse)
def evaluate_submission_api(
    submission_id: int,
    current_student=Depends(get_current_student)
):
    submission = get_submission_by_id(submission_id)
    if not submission:
        raise HTTPException(
            status_code=404,
            detail="Error 404: Submission not found"
        )
    if submission["student_id"] != current_student["student_id"]:
        raise HTTPException(
            status_code=403,
            detail="Error 403: You are not authorized to evaluate this submission"
        )
    return evaluate_submission(submission_id)


@router.get("/submissions/{submission_id}",response_model=SubmissionResponse)
def get_submission(submission_id: int, current_student = Depends(get_current_student)):
    submission = get_submission_by_id(submission_id)
    if not submission:
        raise HTTPException(
            status_code=404, 
            detail="Error 404: Submission not found"
            )
    
    if submission["student_id"] != current_student["student_id"]:
        raise HTTPException(
            status_code=403, 
            detail="Error 403: You are not authorized to view this submission"
            )
    
    return submission