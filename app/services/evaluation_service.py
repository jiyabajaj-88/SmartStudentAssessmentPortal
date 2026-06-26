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
                   q.question_text, q.marks,
                   a.subject
            FROM submitted_answers sa
            JOIN questions q ON sa.question_id = q.question_id
            JOIN submissions s ON sa.submission_id = s.submission_id
            JOIN assessments a ON s.assessment_id = a.assessment_id
            WHERE sa.submission_id = %s
            AND LOWER(q.question_type) = 'subjective'
        """, (submission_id,))
        answers = cur.fetchall()

        for answer in answers:
            marks, feedback = ai_evaluate(
                question=answer["question_text"],
                student_answer=answer["answer_text"],
                max_marks=answer["marks"],
                subject=answer.get("subject", "")
            )
            cur.execute("""
                UPDATE submitted_answers
                SET marks_awarded = %s, feedback = %s
                WHERE answer_id = %s
            """, (marks, feedback, answer["answer_id"]))

        conn.commit()
    finally:
        cur.close()

def ai_evaluate(question: str, student_answer: str, max_marks: int, subject: str = ""):
    if not student_answer or not student_answer.strip():
        return 0, "No answer provided"

    # Determine subject category to adjust rubric
    lang_history_subjects = ["english", "hindi", "history", "political science",
                              "polity", "civics", "geography", "economics",
                              "social science", "social studies", "sst", "literature"]
    
    subject_lower = subject.lower().strip()
    is_humanities = any(s in subject_lower for s in lang_history_subjects)

    # Split marks across rubric parameters based on max_marks
    if max_marks <= 2:
        slots = {"CONCEPTUAL_ACCURACY": 1, "COMPLETENESS": 1}
    elif max_marks == 3:
        slots = {"CONCEPTUAL_ACCURACY": 1, "COMPLETENESS": 1, "KEY_TERMINOLOGY": 1}
    elif max_marks == 4:
        slots = {"CONCEPTUAL_ACCURACY": 2, "COMPLETENESS": 1, "KEY_TERMINOLOGY": 1}
    elif max_marks == 5:
        slots = {"CONCEPTUAL_ACCURACY": 2, "COMPLETENESS": 1, "KEY_TERMINOLOGY": 1, "EXPLANATION_DEPTH": 1}
    else:
        # For high-mark teacher questions (6, 8, 10 etc.) scale proportionally
        quarter = max_marks // 4 or 1
        remaining = max_marks - (quarter * 3)
        slots = {
            "CONCEPTUAL_ACCURACY": remaining,
            "COMPLETENESS": quarter,
            "KEY_TERMINOLOGY": quarter,
            "EXPLANATION_DEPTH": quarter,
        }

    if is_humanities:
        subject_instructions = """
Special instructions for this humanities/language subject:
- For history/polity/economics: reward accurate facts, dates, names, and cause-effect reasoning
- For language/literature: reward expression, coherent argument, and use of textual evidence
- Do NOT penalize if the student writes in simple language — reward clarity of thought
- Award KEY_TERMINOLOGY marks if the student uses subject-specific words (e.g. 'sovereignty', 'osmosis', 'federalism') even once correctly
- For literature questions: a personal interpretation backed by reasoning should get full EXPLANATION_DEPTH marks"""
    else:
        subject_instructions = """
Special instructions for this science/math subject:
- Reward correct use of formulas, units, and scientific terminology
- A correct answer with wrong units loses only KEY_TERMINOLOGY marks, not CONCEPTUAL_ACCURACY
- Do NOT penalize for language quality — if the idea is right, award the marks
- Diagrams or steps described in words count as EXPLANATION_DEPTH"""

    prompt = f"""You are a fair and encouraging examiner evaluating a school student's answer.

Question: {question}
Maximum marks: {max_marks}
Student's answer: {student_answer}

Evaluate using ONLY the following rubric:
{rubric}

General rules:
- Do NOT deduct marks for spelling, grammar, or weak English
- Award partial marks where the student shows partial understanding  
- Be lenient and age-appropriate — if they convey the right idea in simple words, give credit
- Never award more than the marks allocated to each parameter
{subject_instructions}

Respond in EXACTLY this format, nothing else:
{chr(10).join(f'{k}: <marks>/{v} | <one sentence: what was correct or specifically what was missing>' for k, v in slots.items())}
TOTAL: <sum>/{max_marks}
SUMMARY: <one specific, encouraging sentence telling the student exactly what to add to score full marks next time>"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return parse_ai_response(response.text, max_marks)


def parse_ai_response(text: str, max_marks: int):
    total_marks = 0
    feedback_lines = []

    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue

        if line.upper().startswith("TOTAL:"):
            try:
                total_marks = min(int(line.split(":")[1].split("/")[0].strip()), max_marks)
            except (ValueError, IndexError):
                pass

        elif line.upper().startswith("SUMMARY:"):
            summary = line.split(":", 1)[1].strip()
            feedback_lines.append(f"💡 {summary}")

        elif "|" in line and ":" in line:
            # e.g. "CONCEPTUAL_ACCURACY: 2/2 | Correct definition of osmosis"
            try:
                param_part, reason = line.split("|", 1)
                param_name = param_part.split(":")[0].strip().replace("_", " ").title()
                score_part = param_part.split(":")[1].strip()   # "2/2"
                feedback_lines.append(f"{param_name} ({score_part}): {reason.strip()}")
            except (ValueError, IndexError):
                feedback_lines.append(line)

    full_feedback = "\n".join(feedback_lines)
    return total_marks, full_feedback

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