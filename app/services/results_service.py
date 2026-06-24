from app.db import conn
from  psycopg2.extras import RealDictCursor

def create_result(
    submission_id,
    total_marks,
    max_marks,
    overall_feedback
):
    conn.rollback()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            INSERT INTO results
            (
                submission_id,
                total_marks,
                max_marks,
                overall_feedback
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s
            )
            ON CONFLICT (submission_id) DO UPDATE SET
                total_marks = EXCLUDED.total_marks,
                max_marks = EXCLUDED.max_marks,
                overall_feedback = EXCLUDED.overall_feedback
            """,
            (
                submission_id,
                total_marks,
                max_marks,
                overall_feedback
            )
        )

        conn.commit()

        return {
            "message": "Result created successfully"
        }
    finally:
        cur.close()


def get_student_results(student_id):
    conn.rollback()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """SELECT r.result_id, r.submission_id, r.total_marks, r.max_marks, r.overall_feedback
            FROM results r
            JOIN submissions s ON r.submission_id = s.submission_id
            WHERE s.student_id = %s
            """,
            (student_id,)
        )

        return cur.fetchall()
    finally:
        cur.close()
     
def get_results_by_assessment(student_id, assessment_id):
    conn.rollback()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """SELECT r.result_id, r.submission_id, r.total_marks, r.max_marks, r.overall_feedback
            FROM results r
            JOIN submissions s ON r.submission_id = s.submission_id
            WHERE s.student_id = %s AND s.assessment_id = %s
            """,
            (student_id, assessment_id)
        )

        return cur.fetchall()
    finally:
        cur.close()