from app.db import conn
from psycopg2.extras import RealDictCursor


def _group_question_rows(rows):
    questions = {}
    for row in rows:
        question_id = row["question_id"]
        if question_id not in questions:
            questions[question_id] = {
                "question_id": question_id,
                "question_text": row["question_text"],
                "question_type": row["question_type"],
                "marks": row["marks"],
                "options": [],
            }
        if row.get("option_id"):
            questions[question_id]["options"].append(
                {
                    "option_id": row["option_id"],
                    "question_id": question_id,
                    "option_text": row["option_text"],
                }
            )
    return list(questions.values())


def get_questions_by_assessment(assessment_id):
    conn.rollback()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
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
            ORDER BY q.question_id, o.option_id
            """,
            (assessment_id,),
        )
        return _group_question_rows(cur.fetchall())
    finally:
        cur.close()


def get_question_by_id(question_id):
    conn.rollback()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
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
            ORDER BY o.option_id
            """,
            (question_id,),
        )
        rows = cur.fetchall()
        if not rows:
            return None
        return _group_question_rows(rows)[0]
    finally:
        cur.close()
