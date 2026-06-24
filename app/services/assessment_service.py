from app.db import conn
from  psycopg2.extras import RealDictCursor
def get_assessments_for_student(student_class):
    conn.rollback()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            """
            SELECT
                assessment_id,
                title,
                max_marks,
                class AS class_name,
                subject
            FROM assessments
            WHERE TRIM(LOWER(class)) = TRIM(LOWER(%s))
               OR TRIM(LOWER(%s)) LIKE TRIM(LOWER(class)) || '%%'
            ORDER BY assessment_id
            """,
            (student_class, student_class),
        )
        return cur.fetchall()
    finally:
        cur.close()


def get_assessment_by_id(assessment_id):
    conn.rollback()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            """SELECT
                assessment_id,
                title,
                max_marks,
                class AS class_name,
                subject
            FROM assessments
            WHERE assessment_id = %s
            """,
            (assessment_id,)
        )
        return cur.fetchone()
    finally:
        cur.close()