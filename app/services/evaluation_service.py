from app.db import conn
from app.services.results_service import create_result
import psycopg2
from  psycopg2.extras import RealDictCursor
def evaluate_subjective_answers(submission_id):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            SELECT
                sa.answer_id,
                sa.answer_text,
                q.marks
            FROM submitted_answers sa
            JOIN questions q
                ON sa.question_id = q.question_id
            WHERE sa.submission_id = %s
            AND q.question_type = 'subjective'
            """,
            (submission_id,)
        )

        answers = cur.fetchall()

        for answer in answers:

            answer_id = answer["answer_id"]
            answer_text = answer["answer_text"]
            max_marks = answer["marks"]

            if not answer_text:
                marks = 0
                feedback = "Answer too short"
            else:
                word_count = len(answer_text.split())

                if word_count >= 20:

                    marks = max_marks
                    feedback = "Good explanation"

                elif word_count >= 10:

                    marks = max_marks // 2
                    feedback = "Average explanation"

                else:

                    marks = 0
                    feedback = "Answer too short"

            cur.execute(
                """
                UPDATE submitted_answers
                SET marks_awarded = %s,
                    feedback = %s
                WHERE answer_id = %s
                """,
                (
                    marks,
                    feedback,
                    answer_id
                )
            )

        conn.commit()
    finally:
        cur.close()

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
            AND q.question_type = 'objective'
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
        "overall_feedback": feedback,  # renamed from "feedback" to match ResultResponse schema
    }