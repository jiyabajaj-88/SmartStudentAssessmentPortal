from app.db import conn


def create_result(
    submission_id,
    total_marks,
    max_marks,
    overall_feedback
):

    cur = conn.cursor()

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


def get_student_results(student_id):
    cur = conn.cursor()

    cur.execute(
        """SELECT r.result_id, r.submission_id, r.total_marks, r.max_marks, r.overall_feedback
        FROM results r
        JOIN submissions s ON r.submission_id = s.submission_id
        WHERE s.student_id = %s
        """,
        (student_id,)
    )

    return cur.fetchall()
     
def get_results_by_assessment(student_id, assessment_id):
    cur = conn.cursor()

    cur.execute(
        """SELECT r.result_id, r.submission_id, r.total_marks, r.max_marks, r.overall_feedback
        FROM results r
        JOIN submissions s ON r.submission_id = s.submission_id
        WHERE s.student_id = %s AND s.assessment_id = %s
        """,
        (student_id, assessment_id)
    )

    return cur.fetchall()