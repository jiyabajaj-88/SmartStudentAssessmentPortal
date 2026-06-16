from app.db import conn

def get_questions_by_assessment(assessment_id):
    conn.rollback()
    cur=conn.cursor()

    cur.execute(
        """
        SELECT
            q.question_id,
            q.question_text,
            q.question_type,
            q.marks,
            o.option_id,
            o.option_text
        FROM questions q
        LEFT JOIN options o ON q.question_id = o.question_id
        WHERE q.assessment_id = %s
        """,
        (assessment_id,)
    )

    return cur.fetchall()

def get_question_by_id(question_id):
    conn.rollback()
    cur=conn.cursor()

    cur.execute(
        """
        SELECT
            q.question_id,
            q.question_text,
            q.question_type,
            q.marks,
            o.option_id,
            o.option_text
        FROM questions q
        LEFT JOIN options o ON q.question_id = o.question_id
        WHERE q.question_id = %s
        """,
        (question_id,)
    )

    return cur.fetchall()