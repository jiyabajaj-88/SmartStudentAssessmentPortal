from app.db import conn
from app.services.results_service import create_result

def evaluate_subjective_answers(submission_id):

    cur = conn.cursor()

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

        answer_id = answer[0]
        answer_text = answer[1]
        max_marks = answer[2]

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

def evaluate_objective_answers(submission_id):

    cur = conn.cursor()

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

        answer_id = answer[0]
        selected_option_id = answer[1]
        correct_option_id = answer[2]
        question_marks = answer[3]

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

def calculate_total_marks(submission_id):

    cur = conn.cursor()

    cur.execute(
        """
        SELECT COALESCE(
            SUM(marks_awarded),
            0
        )
        FROM submitted_answers
        WHERE submission_id = %s
        """,
        (submission_id,)
    )

    total_marks = cur.fetchone()[0]

    return total_marks


def get_max_marks(submission_id):

    cur = conn.cursor()

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

    max_marks = cur.fetchone()[0]

    return max_marks

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

    cur = conn.cursor()

    cur.execute(
        """
        UPDATE submissions
        SET status = 'Evaluated'
        WHERE submission_id = %s
        """,
        (submission_id,)
    )

    conn.commit()

    return {
        "submission_id": submission_id,
        "total_marks": total_marks,
        "max_marks": max_marks,
        "feedback": feedback
    }
