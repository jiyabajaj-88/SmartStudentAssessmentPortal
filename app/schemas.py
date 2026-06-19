from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class StudentRegister(BaseModel):
    name: str
    email: str
    password: str
    student_class: str
    school: str


class StudentLogin(BaseModel):
    email: str
    password: str


class Student(BaseModel):
    name: str
    student_class: str
    email: str
    school: str

class AnswerRequest(BaseModel):
    question_id: int
    selected_option_id: Optional[int] = None
    answer_text: Optional[str] = None

class AnswerUpdate(BaseModel):
    selected_option_id: Optional[int] = None
    answer_text: Optional[str] = None


class StudentResponse(BaseModel):
    student_id: int
    name: str
    email: str
    student_class: str
    school: str

class AssessmentResponse(BaseModel):
    assessment_id: int
    title: str
    max_marks: int
    class_name: str
    subject: str

    class Config:
        from_attributes = True


class QuestionResponse(BaseModel):
    question_id: int
    question_text: str
    question_type: str
    marks: int

    class Config:
        from_attributes = True


class QuestionWithOptionsResponse(BaseModel):
    question_id: int
    question_text: str
    question_type: str
    marks: int
    options: List["OptionResponse"] = []

    class Config:
        from_attributes = True


class OptionResponse(BaseModel):
    option_id: int
    question_id: int
    option_text: str

    class Config:
        from_attributes = True


class SubmissionResponse(BaseModel):
    submission_id: int
    student_id: int
    assessment_id: int
    status: str
    submitted_at: datetime

    class Config:
        from_attributes = True


class SubmittedAnswerResponse(BaseModel):
    answer_id: int
    question_id: int
    selected_option_id: Optional[int] = None
    answer_text: Optional[str] = None
    marks_awarded: Optional[int] = None
    feedback: Optional[str] = None

    class Config:
        from_attributes = True


class ResultResponse(BaseModel):
    result_id: Optional[int] = None
    submission_id: int
    total_marks: int
    max_marks: int
    overall_feedback: Optional[str] = None

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    message: str