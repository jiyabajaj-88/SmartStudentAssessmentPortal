from app.db import conn

from passlib.context import CryptContext
from app.auth import create_access_token

import psycopg2
from  psycopg2.extras import RealDictCursor


def register_student(student):
    conn.rollback()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """SELECT student_id FROM students WHERE email = %s""",
        (student.email,)
    )
    existing_student = cur.fetchone()

    if existing_student:
        cur.close()
        return None, "Email already registered"  

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
    cur = conn.cursor(cursor_factory=RealDictCursor)

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

    if not pwd_context.verify(password, student["password"]):
        cur.close()
        return None, "Invalid password"  

    access_token = create_access_token({
        "student_id": student["student_id"],
        "email": student["email"],
        "student_class": student["student_class"]
    })

    cur.close()

    return {"access_token": access_token, "token_type": "bearer"}, None  # ✅ tuple   

def get_user_profile(student_id):

    cur = conn.cursor(cursor_factory=RealDictCursor)

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
        "student_id": student["student_id"],
        "name": student["name"],
        "email": student["email"],
        "student_class": student["student_class"],
        "school": student["school"]
    }