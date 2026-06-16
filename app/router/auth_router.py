from fastapi import APIRouter, Depends,HTTPException
from app.services.auth_service import register_student, login_student, get_user_profile
from fastapi.security import OAuth2PasswordRequestForm
from dependencies import get_current_student  
from app.schemas import StudentRegister

router = APIRouter()

@router.post("/register", status_code=201)
def register(student: StudentRegister):
    result, error = register_student(student)
    if error == "Email already registered":
        raise HTTPException(status_code=409, detail=error)
    return {"message": "Student registered successfully"}

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    result, error = login_student(form_data.username, form_data.password)
    if error == "Student not found":
        raise HTTPException(status_code=404, detail=error)
    if error == "Invalid password":
        raise HTTPException(status_code=401, detail=error)
    return result

@router.get("/profile")
def get_profile(current_student=Depends(get_current_student)):
    student = get_user_profile(current_student["student_id"])
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student