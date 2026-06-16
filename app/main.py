from fastapi import FastAPI

from fastapi.security import OAuth2PasswordBearer

from app.router import answers, assessments, auth_router, results
from app.router import submissions

from app.schemas import Student
from fastapi.middleware.cors import CORSMiddleware


from app.services.student_service import(
    get_student_by_id,
    create_student
)

app=FastAPI()


app.include_router(auth_router.router)
app.include_router(assessments.router)
app.include_router(submissions.router)
app.include_router(answers.router)
app.include_router(results.router)


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/login"
    )


@app.get("/students/{student_id}")
def student(student_id: int):
    return get_student_by_id(student_id)

@app.post("/students")
def add_student(student: Student):
    return create_student(
        student.name,
        student.student_class, 
        student.email, 
        student.school
        )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this in production
    allow_methods=["*"],
    allow_headers=["*"],
)