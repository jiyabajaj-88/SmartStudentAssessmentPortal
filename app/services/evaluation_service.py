from app.db import conn
from app.services.results_service import create_result
from  psycopg2.extras import RealDictCursor
from google import genai
import os

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def evaluate_subjective_answers(submission_id):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT sa.answer_id, sa.answer_text,
                   q.question_text, q.marks
            FROM submitted_answers sa
            JOIN questions q ON sa.question_id = q.question_id
            WHERE sa.submission_id = %s
            AND LOWER(q.question_type) = 'subjective'
        """, (submission_id,))
        answers = cur.fetchall()

        for answer in answers:
            marks, feedback = ai_evaluate(
                question=answer["question_text"],
                student_answer=answer["answer_text"],
                max_marks=answer["marks"]
            )
            cur.execute("""
                UPDATE submitted_answers
                SET marks_awarded = %s, feedback = %s
                WHERE answer_id = %s
            """, (marks, feedback, answer["answer_id"]))

        conn.commit()
    finally:
        cur.close()

def ai_evaluate(question: str, student_answer: str, max_marks: int):
    if not student_answer or not student_answer.strip():
        return 0, "No answer provided"

    prompt = f"""You are a strict but fair teacher evaluating a student's answer.

Question: {question}
Max marks: {max_marks}
Student's answer: {student_answer}

Evaluate the answer and respond in this exact format:
MARKS: <integer between 0 and {max_marks}>
FEEDBACK: <one sentence of constructive feedback>

Be concise. Only output these two lines."""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return parse_ai_response(response.text, max_marks)


def parse_ai_response(text: str, max_marks: int):
    marks = 0
    feedback = "Could not evaluate"
    for line in text.strip().splitlines():
        if line.startswith("MARKS:"):
            try:
                marks = min(int(line.split(":")[1].strip()), max_marks)
            except ValueError:
                marks = 0
        elif line.startswith("FEEDBACK:"):
            feedback = line.split(":", 1)[1].strip()
    return marks, feedback

def evaluate_objective_answers(submission_id):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            SELECT
                sa.answer_id,
                sa.selected_option_id,
                o.option_id,
                q.marks
            FROM submitted_answers sa
            JOIN questions q
                ON sa.question_id = q.question_id
            JOIN options o
                ON q.question_id = o.question_id
            WHERE sa.submission_id = %s
            AND UPPER(q.question_type) = 'OBJECTIVE'
            AND o.is_correct = TRUE
            """,
            (submission_id,)
        )

        answers = cur.fetchall()

        for answer in answers:

            answer_id = answer["answer_id"]
            selected_option_id = answer["selected_option_id"]
            correct_option_id = answer["option_id"]
            question_marks = answer["marks"]

            if selected_option_id == correct_option_id:

                cur.execute(
                    """
                    UPDATE submitted_answers
                    SET marks_awarded = %s,
                        feedback = %s
                    WHERE answer_id = %s
                    """,
                    (
                        question_marks,
                        "Correct Answer",
                        answer_id
                    )
                )

            else:

                cur.execute(
                    """
                    UPDATE submitted_answers
                    SET marks_awarded = 0,
                        feedback = %s
                    WHERE answer_id = %s
                    """,
                    (
                        "Incorrect Answer",
                        answer_id
                    )
                )

        conn.commit()
    finally:
        cur.close()

def calculate_total_marks(submission_id):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            SELECT COALESCE(
                SUM(marks_awarded),
                0
            ) AS total_marks
            FROM submitted_answers
            WHERE submission_id = %s
            """,
            (submission_id,)
        )

        total_marks = cur.fetchone()["total_marks"]

        return total_marks
    finally:
        cur.close()


def get_max_marks(submission_id):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            SELECT a.max_marks
            FROM submissions s
            JOIN assessments a
                ON s.assessment_id = a.assessment_id
            WHERE s.submission_id = %s
            """,
            (submission_id,)
        )

        max_marks = cur.fetchone()["max_marks"]

        return max_marks
    finally:
        cur.close()

def generate_overall_feedback(
    total_marks,
    max_marks
):
    if max_marks == 0:
        return "No marks available"

    percentage = (
        total_marks / max_marks
    ) * 100

    if percentage >= 90:

        return "Excellent Performance"

    elif percentage >= 75:

        return "Very Good Performance"

    elif percentage >= 50:

        return "Good Performance"

    else:

        return "Needs Improvement"
    

def evaluate_submission(submission_id):

    evaluate_objective_answers(
        submission_id
    )

    evaluate_subjective_answers(
        submission_id
    )

    total_marks = calculate_total_marks(
        submission_id
    )

    max_marks = get_max_marks(
        submission_id
    )

    feedback = generate_overall_feedback(
        total_marks,
        max_marks
    )

    create_result(
        submission_id,
        total_marks,
        max_marks,
        feedback
    )

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            UPDATE submissions
            SET status = 'Evaluated'
            WHERE submission_id = %s
            """,
            (submission_id,)
        )

        conn.commit()
    finally:
        cur.close()

    return {
        "submission_id": submission_id,
        "total_marks": total_marks,
        "max_marks": max_marks,
        "overall_feedback": feedback,  
    }