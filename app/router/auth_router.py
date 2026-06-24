from fastapi import APIRouter, Depends, HTTPException
from app.services.auth_service import register_student, login_student, get_user_profile
from fastapi.security import OAuth2PasswordRequestForm
from app.dependencies import get_current_student  
from app.schemas import StudentRegister, StudentResponse

router = APIRouter()

@router.post("/register", status_code=201)
def register(student: StudentRegister):
    result, error = register_student(student)
    # BUG 13 FIX: Catch ALL errors, not just exact "Email already registered"
    if error:
        if error == "Email already registered":
            raise HTTPException(status_code=409, detail=error)
        raise HTTPException(status_code=500, detail="Registration failed: " + error)
    return {"message": "Student registered successfully"}

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    result, error = login_student(form_data.username, form_data.password)
    # BUG 14 FIX: Return generic 401 for both bad email and bad password
    # to prevent user enumeration attacks
    if error:
        raise HTTPException(
            status_code=401, 
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return result

@router.get("/profile", response_model=StudentResponse)
def get_profile(current_student=Depends(get_current_student)):
    student = get_user_profile(current_student["student_id"])
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student