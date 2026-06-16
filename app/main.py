from fastapi import FastAPI

from fastapi.security import OAuth2PasswordBearer

from app.router import answers, assessments, auth_router, results
from app.router import submissions

from app.schemas import StudentResponse
from fastapi.middleware.cors import CORSMiddleware


from app.services.student_service import get_student_by_id

app=FastAPI()

# Middleware must be added before routers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(assessments.router)
app.include_router(submissions.router)
app.include_router(answers.router)
app.include_router(results.router)


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/login"
    )


@app.get("/students/{student_id}", response_model=StudentResponse)
def student(student_id: int):
    return get_student_by_id(student_id)