from app.db import conn

def submit_answer(submission_id, question_id, selected_option_id=None, answer_text=None):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO submitted_answers (submission_id, question_id, selected_option_id, answer_text)
        VALUES (%s, %s, %s, %s)
        RETURNING answer_id
    """, (submission_id, question_id, selected_option_id, answer_text))
    answer_id = cur.fetchone()[0]
    conn.commit()
    return {"message": "Answer submitted", "answer_id": answer_id}

def update_answer(
    answer_id,
    selected_option_id=None,
    answer_text=None
):
    cur = conn.cursor()

    if selected_option_id is not None:

        cur.execute(
            """
            UPDATE submitted_answers
            SET selected_option_id = %s
            WHERE answer_id = %s
            """,
            (selected_option_id, answer_id)
        )

    elif answer_text is not None:

        cur.execute(
            """
            UPDATE submitted_answers
            SET answer_text = %s
            WHERE answer_id = %s
            """,
            (answer_text, answer_id)
        )

    else:
        return {
            "message": "No answer provided"
        }

    conn.commit()

    return {
        "message": "Answer updated successfully"
    }

def get_answers_by_submission(submission_id):
    conn.rollback()
    cur=conn.cursor()

    cur.execute(
        """SELECT answer_id, question_id, selected_option_id
        FROM submitted_answers
        WHERE submission_id = %s
        """,
        (submission_id,)
    )

    return cur.fetchall()