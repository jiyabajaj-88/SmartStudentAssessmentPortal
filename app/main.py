from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.router import answers, assessments, auth_router, results, ai_practice
from app.router import submissions
from app.schemas import StudentResponse
from app.services.student_service import get_student_by_id
from app.dependencies import get_current_student

app = FastAPI()

# Middleware must be added before routers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_charset_header(request, call_next):
    response = await call_next(request)
    if "text/html" in response.headers.get("content-type", ""):
        response.headers["content-type"] = "text/html; charset=utf-8"
    return response


app.include_router(auth_router.router)
app.include_router(assessments.router)
app.include_router(submissions.router)
app.include_router(answers.router)
app.include_router(results.router)
app.include_router(ai_practice.router)



# BUG 6 FIX: Added authentication + null check for missing student
@app.get("/students/{student_id}", response_model=StudentResponse)
def student(student_id: int, current_student=Depends(get_current_student)):
    result = get_student_by_id(student_id)
    if not result:
        raise HTTPException(status_code=404, detail="Student not found")
    return result