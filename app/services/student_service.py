from app.db import conn
from  psycopg2.extras import RealDictCursor


def get_student_by_id(student_id):
    conn.rollback()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            """SELECT student_id, name, email, student_class, school
            FROM students
            WHERE student_id = %s
            """,
            (student_id,)
        )
        return cur.fetchone()
    finally:
        cur.close()


def create_student(name, student_class, email, school, password):
    conn.rollback()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            """INSERT INTO students (name, student_class, email, school, password)
               VALUES (%s, %s, %s, %s, %s)
               """,
            (name, student_class, email, school, password)
        )
        conn.commit()
        return {"message": "Student created successfully"}
    finally:
        cur.close()