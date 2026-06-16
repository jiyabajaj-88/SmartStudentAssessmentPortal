from pydantic import BaseModel

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
    selected_option_id: int = None
    answer_text: str = None

class AnswerUpdate(BaseModel):
    selected_option_id: int = None
    answer_text: str = None