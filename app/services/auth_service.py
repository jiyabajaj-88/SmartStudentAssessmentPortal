from app.db import conn

from passlib.context import CryptContext
from app.auth import create_access_token

from  psycopg2.extras import RealDictCursor

# Module-level singleton — CryptContext is expensive to instantiate (BUG 12)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def register_student(student):
    conn.rollback()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            """SELECT student_id FROM students WHERE email = %s""",
            (student.email,)
        )
        existing_student = cur.fetchone()

        if existing_student:
            return None, "Email already registered"

        hashed_password = pwd_context.hash(student.password)

        cur.execute(
            """INSERT INTO students (name, email, password, student_class, school)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING student_id""",
            (student.name, student.email, hashed_password, student.student_class, student.school)
        )
        conn.commit()

        return {"message": "Student registered successfully"}, None  # (result, error)
    except Exception as e:
        conn.rollback()
        return None, str(e)
    finally:
        cur.close()

def login_student(email, password):
    conn.rollback()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
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
            return None, "Student not found"

        if not pwd_context.verify(password, student["password"]):
            return None, "Invalid password"

        access_token = create_access_token({
            "student_id": student["student_id"],
            "email": student["email"],
            "student_class": student["student_class"]
        })

        return {"access_token": access_token, "token_type": "bearer"}, None  # ✅ tuple
    finally:
        cur.close()

def get_user_profile(student_id):
    conn.rollback()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
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

        if not student:
            return None  # BUG 3 FIX: was returning {"message": ...} which is truthy

        return {
            "student_id": student["student_id"],
            "name": student["name"],
            "email": student["email"],
            "student_class": student["student_class"],
            "school": student["school"]
        }
    finally:
        cur.close()