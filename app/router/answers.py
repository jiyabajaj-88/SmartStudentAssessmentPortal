from fastapi import APIRouter, Depends, HTTPException
from app.schemas import AnswerRequest, AnswerUpdate
from app.services.answers_service import submit_answer, update_answer
from app.services.submission_service import get_submission_by_id
from dependencies import get_current_student
from app.schemas import MessageResponse
router = APIRouter()

@router.post("/submissions/{submission_id}/answers",response_model=MessageResponse)
def submit_answers(
    submission_id: int,
    answers: list[AnswerRequest],
    current_student = Depends(get_current_student)
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
            detail="Error 403: You are not authorized to submit answers for this submission"
            )
    
    for answer in answers:
        submit_answer(
            submission_id,
            answer.question_id,
            answer.selected_option_id,
            answer.answer_text,
        )
    
    return {"message": "status 200: Answers submitted successfully"}

@router.put("/answers/{answer_id}", response_model=MessageResponse)
def update_answer_api(
    answer_id: int,
    answer: AnswerUpdate,
    current_student = Depends(get_current_student)
):
    return update_answer(
        answer_id,
        answer.selected_option_id,
        answer.answer_text
    )
