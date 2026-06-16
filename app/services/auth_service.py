from app.db import conn

from passlib.context import CryptContext
from app.auth import create_access_token




def register_student(student):
    cur = conn.cursor()
    cur.execute(
        """SELECT student_id FROM students WHERE email = %s""",
        (student.email,)
    )
    existing_student = cur.fetchone()

    if existing_student:
        cur.close()
        return None, "Email already registered"  # (result, error)

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password = pwd_context.hash(student.password)

    cur.execute(
        """INSERT INTO students (name, email, password, student_class, school)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING student_id""",
        (student.name, student.email, hashed_password, student.student_class, student.school)
    )
    conn.commit()
    cur.close()

    return {"message": "Student registered successfully"}, None  # (result, error)

def login_student(email, password):
    cur = conn.cursor()

    cur.execute(
        """
        SELECT student_id, name, email, password, student_class
        FROM students
        WHERE email = %s
        """,
        (email,)
    )

    student = cur.fetchone()

    if not student:
        cur.close()
        return None, "Student not found"  

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    if not pwd_context.verify(password, student[3]):
        cur.close()
        return None, "Invalid password"  

    access_token = create_access_token({
        "student_id": student[0],
        "email": student[2],
        "student_class": student[4]
    })

    cur.close()

    return {"access_token": access_token, "token_type": "bearer"}, None  # ✅ tuple   

def get_user_profile(student_id):

    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            student_id,
            name,
            email,
            student_class,
            school
        FROM students
        WHERE student_id = %s
        """,
        (student_id,)
    )

    student = cur.fetchone()

    cur.close()

    if not student:
        return {
            "message": "Student not found"
        }

    return {
        "student_id": student[0],
        "name": student[1],
        "email": student[2],
        "student_class": student[3],
        "school": student[4]
    }