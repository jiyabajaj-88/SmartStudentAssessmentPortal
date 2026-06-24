from app.db import conn
from  psycopg2.extras import RealDictCursor

def submit_answer(submission_id, question_id, selected_option_id=None, answer_text=None):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
        INSERT INTO submitted_answers (submission_id, question_id, selected_option_id, answer_text)
        VALUES (%s, %s, %s, %s)
        RETURNING answer_id
    """, (submission_id, question_id, selected_option_id, answer_text))
        answer_id = cur.fetchone()["answer_id"]
        conn.commit()
        return {"message": "Answer submitted", "answer_id": answer_id}
    finally:
        cur.close()

def update_answer(
    answer_id,
    selected_option_id=None,
    answer_text=None
):
    conn.rollback()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # BUG 17 FIX: Use separate if statements instead of elif,
        # so both fields can be updated in a single call
        if selected_option_id is not None:
            cur.execute(
                """
                UPDATE submitted_answers
                SET selected_option_id = %s
                WHERE answer_id = %s
                """,
                (selected_option_id, answer_id)
            )

        if answer_text is not None:
            cur.execute(
                """
                UPDATE submitted_answers
                SET answer_text = %s
                WHERE answer_id = %s
                """,
                (answer_text, answer_id)
            )

        if selected_option_id is None and answer_text is None:
            return {
                "message": "No answer provided"
            }

        conn.commit()

        return {
            "message": "Answer updated successfully"
        }
    finally:
        cur.close()

def get_answers_by_submission(submission_id):
    conn.rollback()
    cur=conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
        """SELECT answer_id, question_id, selected_option_id, answer_text,
                  marks_awarded, feedback
        FROM submitted_answers
        WHERE submission_id = %s
        ORDER BY answer_id
        """,
        (submission_id,)
    )
        return cur.fetchall()
    finally:
        cur.close()


def get_answer_by_id(answer_id):
    """Fetch a single answer by its ID. Used for ownership verification (BUG 11)."""
    conn.rollback()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            """SELECT sa.answer_id, sa.submission_id, s.student_id
            FROM submitted_answers sa
            JOIN submissions s ON sa.submission_id = s.submission_id
            WHERE sa.answer_id = %s
            """,
            (answer_id,)
        )
        return cur.fetchone()
    finally:
        cur.close()