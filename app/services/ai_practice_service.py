"""
app/services/ai_practice_service.py

All Gemini interaction, prompt engineering, and business logic
for the AI Practice feature lives here.
The router only validates requests and calls these functions.
"""

import os
import json
import re

from psycopg2.extras import RealDictCursor
from fastapi import HTTPException
from google import genai

from app.db import conn

_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash"]

HUMANITIES = [
    "english", "hindi", "history", "political science", "polity",
    "civics", "geography", "economics", "social science",
    "social studies", "sst", "literature", "sanskrit", "urdu",
]


def _is_humanities(subject: str) -> bool:
    return any(h in subject.lower() for h in HUMANITIES)



def _call_gemini(prompt: str) -> str:
    """Call Gemini with automatic model fallback on quota/overload errors."""
    last_err = ""
    for model in _MODELS:
        try:
            response = _client.models.generate_content(model=model, contents=prompt)
            return response.text.strip()
            if isinstance(text, bytes):
                text = text.decode('utf-8')
            return text.strip()
        except Exception as e:
            err_str = str(e)
            last_err = err_str
            # retry next model on transient errors; raise immediately for others
            if any(k in err_str.lower() for k in ("quota", "429", "503", "overloaded", "unavailable")):
                continue
            raise HTTPException(status_code=500, detail=f"Gemini error ({model}): {err_str}")
    raise HTTPException(status_code=503, detail=f"All AI models are currently unavailable. {last_err}")


def _parse_json(raw: str):
    """Strip markdown fences and parse JSON."""
    raw = re.sub(r"^```[a-z]*\n?", "", raw.strip())
    raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw.strip())


def generate_assessment(student_id: int, student_class: str, subject: str, topic: str) -> dict:
    """
    Call Gemini to generate 5 MCQ + 3 subjective questions,
    persist them to the DB, and return the full assessment.
    """
    is_hum = _is_humanities(subject)

    if is_hum:
        subj_instructions = (
            "For subjective questions ask for: cause and effect, significance, "
            "comparison, or analysis — not just definitions. "
            "Reward expression and reasoning over rote facts."
        )
    else:
        subj_instructions = (
            "For subjective questions ask students to explain a process, "
            "derive a result, or describe an experiment with steps."
        )

    prompt = f"""You are an expert teacher creating a practice assessment for a school student.

Topic: {topic}
Subject: {subject}
Class: {student_class}

Generate exactly 8 questions: 5 objective (MCQ) and 3 subjective.
{subj_instructions}

Return ONLY a valid JSON array — no markdown, no explanation, no code fences.

Each question must follow this exact schema:

For objective:
{{
  "question_text": "...",
  "question_type": "objective",
  "marks": 1,
  "correct_answer": "<exact text of the correct option>",
  "options": [
    {{"option_text": "...", "is_correct": false}},
    {{"option_text": "...", "is_correct": false}},
    {{"option_text": "...", "is_correct": true}},
    {{"option_text": "...", "is_correct": false}}
  ]
}}

For subjective:
{{
  "question_text": "...",
  "question_type": "subjective",
  "marks": <3 or 5 only — never any other value>,
  "correct_answer": "",
  "options": []
}}

Hard rules:
- Objective: exactly 4 options, exactly 1 is_correct = true, marks always = 1
- Subjective: marks must be EITHER 3 OR 5, never 2 or 4 or 10
- Aim for two 3-mark and one 5-mark subjective question
- Vary difficulty: 2 easy, 3 medium, 3 hard across all 8 questions
- Questions should be appropriate for class {student_class} level
- Use only standard ASCII characters in question text. Write "x^2" instead of "x²", "alpha" instead of "α", "beta" instead of "β", "..." instead of "…" """

    raw = _call_gemini(prompt)
    try:
        questions_data = _parse_json(raw)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini returned invalid JSON: {str(e)}")

    if not isinstance(questions_data, list) or not questions_data:
        raise HTTPException(status_code=500, detail="Gemini did not return a valid question list")

    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        max_marks = sum(q.get("marks", 1) for q in questions_data)
        title = f"Practice: {topic} ({subject})"

        cur.execute(
            """
            INSERT INTO practice_assessments
                (student_id, topic, subject, title, max_marks, status)
            VALUES (%s, %s, %s, %s, %s, 'Pending')
            RETURNING practice_assessment_id, student_id, topic, subject,
                      title, max_marks, status, created_at
            """,
            (student_id, topic, subject, title, max_marks),
        )
        assessment = dict(cur.fetchone())
        pa_id = assessment["practice_assessment_id"]

        saved_questions = []
        for order, q in enumerate(questions_data):
            cur.execute(
                """
                INSERT INTO practice_questions
                    (practice_assessment_id, question_text, question_type,
                     marks, correct_answer, options, display_order)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING practice_question_id, question_text, question_type,
                          marks, display_order
                """,
                (
                    pa_id,
                    q["question_text"],
                    q["question_type"].lower(),
                    q.get("marks", 1),
                    q.get("correct_answer", ""),
                    json.dumps(q.get("options", [])),
                    order,
                ),
            )
            question = dict(cur.fetchone())
            # Never expose is_correct to the client
            question["options"] = [
                {"option_text": o["option_text"]}
                for o in q.get("options", [])
            ]
            saved_questions.append(question)

        conn.commit()
        assessment["questions"] = saved_questions
        return assessment

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save practice assessment: {str(e)}")
    finally:
        cur.close()



def list_assessments(student_id: int) -> list:
    """Return all practice assessments for a student, newest first."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            """
            SELECT pa.practice_assessment_id, pa.topic, pa.subject,
                   pa.title, pa.max_marks, pa.status, pa.created_at,
                   pr.total_marks, pr.overall_feedback
            FROM practice_assessments pa
            LEFT JOIN practice_results pr
                   ON pa.practice_assessment_id = pr.practice_assessment_id
            WHERE pa.student_id = %s
            ORDER BY pa.created_at DESC
            """,
            (student_id,),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()



def get_assessment(practice_assessment_id: int, student_id: int) -> dict:
    """Fetch a practice assessment and its questions (options without is_correct)."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            """
            SELECT practice_assessment_id, student_id, topic, subject,
                   title, max_marks, status, created_at
            FROM practice_assessments
            WHERE practice_assessment_id = %s AND student_id = %s
            """,
            (practice_assessment_id, student_id),
        )
        assessment = cur.fetchone()
        if not assessment:
            raise HTTPException(status_code=404, detail="Practice assessment not found")
        assessment = dict(assessment)

        cur.execute(
            """
            SELECT practice_question_id, question_text, question_type,
                   marks, options, display_order
            FROM practice_questions
            WHERE practice_assessment_id = %s
            ORDER BY display_order
            """,
            (practice_assessment_id,),
        )
        questions = []
        for row in cur.fetchall():
            q = dict(row)
            raw_opts = q.get("options") or []
            if isinstance(raw_opts, str):
                raw_opts = json.loads(raw_opts)
            q["options"] = [{"option_text": o["option_text"]} for o in raw_opts] if raw_opts else []
            questions.append(q)

        assessment["questions"] = questions
        return assessment
    finally:
        cur.close()


def save_answers(practice_assessment_id: int, student_id: int, answers: list) -> dict:
    """
    Persist student answers.
    Each answer: {practice_question_id, answer_text?, selected_option_text?}
    """
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            "SELECT student_id FROM practice_assessments WHERE practice_assessment_id = %s",
            (practice_assessment_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Practice assessment not found")
        if row["student_id"] != student_id:
            raise HTTPException(status_code=403, detail="Not authorised")

        for ans in answers:
            cur.execute(
                """
                INSERT INTO practice_answers
                    (practice_assessment_id, practice_question_id,
                     answer_text, selected_option_text)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (practice_assessment_id, practice_question_id)
                DO UPDATE SET
                    answer_text          = EXCLUDED.answer_text,
                    selected_option_text = EXCLUDED.selected_option_text
                """,
                (
                    practice_assessment_id,
                    ans["practice_question_id"],
                    ans.get("answer_text"),
                    ans.get("selected_option_text"),
                ),
            )

        cur.execute(
            "UPDATE practice_assessments SET status = 'Submitted' WHERE practice_assessment_id = %s",
            (practice_assessment_id,),
        )
        conn.commit()
        return {"message": "Answers submitted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()


def evaluate_submission(practice_assessment_id: int, student_id: int) -> dict:
    """
    Grade all answers:
      - Objective: local string match against stored correct_answer (no Gemini)
      - Subjective: Gemini rubric-based evaluation
    Saves marks + feedback, writes to practice_results.
    """
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            "SELECT student_id, subject, status FROM practice_assessments WHERE practice_assessment_id = %s",
            (practice_assessment_id,),
        )
        assessment = cur.fetchone()
        if not assessment:
            raise HTTPException(status_code=404, detail="Practice assessment not found")
        if assessment["student_id"] != student_id:
            raise HTTPException(status_code=403, detail="Not authorised")
        if assessment["status"] == "Pending":
            raise HTTPException(status_code=400, detail="Answers not submitted yet")

        subject = assessment["subject"]

        cur.execute(
            """
            SELECT pa.practice_answer_id,
                   pa.answer_text,
                   pa.selected_option_text,
                   pq.practice_question_id,
                   pq.question_text,
                   pq.question_type,
                   pq.marks,
                   pq.correct_answer
            FROM practice_answers pa
            JOIN practice_questions pq
                ON pa.practice_question_id = pq.practice_question_id
            WHERE pa.practice_assessment_id = %s
            """,
            (practice_assessment_id,),
        )
        answers = cur.fetchall()

        for ans in answers:
            if ans["question_type"] == "objective":
                # Local grading — no Gemini needed
                student_pick = (ans["selected_option_text"] or "").strip().lower()
                correct = (ans["correct_answer"] or "").strip().lower()
                if student_pick and student_pick == correct:
                    marks, feedback = ans["marks"], "Correct answer!"
                else:
                    marks, feedback = 0, f"Incorrect. The correct answer is: {ans['correct_answer']}"
            else:
                # Subjective — Gemini rubric evaluation
                marks, feedback = _ai_evaluate_subjective(
                    question=ans["question_text"],
                    student_answer=ans["answer_text"] or "",
                    max_marks=ans["marks"],
                    subject=subject,
                )

            cur.execute(
                "UPDATE practice_answers SET marks_awarded = %s, feedback = %s WHERE practice_answer_id = %s",
                (marks, feedback, ans["practice_answer_id"]),
            )

        conn.commit()

        cur.execute(
            "SELECT COALESCE(SUM(marks_awarded), 0) AS total FROM practice_answers WHERE practice_assessment_id = %s",
            (practice_assessment_id,),
        )
        total = cur.fetchone()["total"]

        cur.execute(
            "SELECT max_marks FROM practice_assessments WHERE practice_assessment_id = %s",
            (practice_assessment_id,),
        )
        max_marks = cur.fetchone()["max_marks"]

        overall = _overall_feedback(total, max_marks)

        cur.execute(
            """
            INSERT INTO practice_results
                (practice_assessment_id, total_marks, max_marks, overall_feedback)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (practice_assessment_id) DO UPDATE SET
                total_marks      = EXCLUDED.total_marks,
                max_marks        = EXCLUDED.max_marks,
                overall_feedback = EXCLUDED.overall_feedback,
                evaluated_at     = NOW()
            """,
            (practice_assessment_id, total, max_marks, overall),
        )
        cur.execute(
            "UPDATE practice_assessments SET status = 'Evaluated' WHERE practice_assessment_id = %s",
            (practice_assessment_id,),
        )
        conn.commit()

        return {
            "practice_assessment_id": practice_assessment_id,
            "total_marks": int(total),
            "max_marks": max_marks,
            "overall_feedback": overall,
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()


def get_result(practice_assessment_id: int, student_id: int) -> dict:
    """Return result summary + per-question breakdown (with correct answers exposed)."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            """
            SELECT pr.practice_result_id, pr.practice_assessment_id,
                   pr.total_marks, pr.max_marks, pr.overall_feedback,
                   pr.evaluated_at, pa.title, pa.topic, pa.subject
            FROM practice_results pr
            JOIN practice_assessments pa
                ON pr.practice_assessment_id = pa.practice_assessment_id
            WHERE pr.practice_assessment_id = %s AND pa.student_id = %s
            """,
            (practice_assessment_id, student_id),
        )
        result = cur.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Result not found")
        result = dict(result)

        cur.execute(
            """
            SELECT pq.practice_question_id, pq.question_text,
                   pq.question_type, pq.marks AS max_question_marks,
                   pq.correct_answer, pq.options,
                   pa.answer_text, pa.selected_option_text,
                   pa.marks_awarded, pa.feedback
            FROM practice_questions pq
            LEFT JOIN practice_answers pa
                   ON pq.practice_question_id = pa.practice_question_id
                  AND pa.practice_assessment_id = %s
            WHERE pq.practice_assessment_id = %s
            ORDER BY pq.display_order
            """,
            (practice_assessment_id, practice_assessment_id),
        )
        breakdown = []
        for row in cur.fetchall():
            r = dict(row)
            raw_opts = r.get("options") or []
            if isinstance(raw_opts, str):
                raw_opts = json.loads(raw_opts)
            # Expose full options with is_correct for result review
            r["options"] = raw_opts if raw_opts else []
            breakdown.append(r)

        result["question_breakdown"] = breakdown
        return result
    finally:
        cur.close()


def _ai_evaluate_subjective(
    question: str, student_answer: str, max_marks: int, subject: str
) -> tuple:
    """Use Gemini to grade a subjective answer with a rubric adapted to subject type."""
    if not student_answer.strip():
        return 0, "No answer provided."

    is_hum = _is_humanities(subject)

    # Build rubric slots scaled to max_marks
    if max_marks <= 2:
        slots = {"CONCEPTUAL_ACCURACY": 1, "COMPLETENESS": 1}
    elif max_marks == 3:
        slots = {"CONCEPTUAL_ACCURACY": 1, "COMPLETENESS": 1, "KEY_TERMINOLOGY": 1}
    elif max_marks == 4:
        slots = {"CONCEPTUAL_ACCURACY": 2, "COMPLETENESS": 1, "KEY_TERMINOLOGY": 1}
    else:  # 5
        slots = {
            "CONCEPTUAL_ACCURACY": 2,
            "COMPLETENESS": 1,
            "KEY_TERMINOLOGY": 1,
            "EXPLANATION_DEPTH": 1,
        }

    rubric_lines = "\n".join(
        f"{k}: out of {v} mark{'s' if v > 1 else ''}" for k, v in slots.items()
    )
    response_format = "\n".join(
        f"{k}: <marks>/{v} | <one sentence: what was correct or specifically what was missing>"
        for k, v in slots.items()
    )

    if is_hum:
        subject_note = """Subject-specific rules (humanities):
- Reward accurate facts, dates, names, cause-effect reasoning
- For literature: reward coherent argument and textual evidence
- A personal interpretation backed by reasoning gets full EXPLANATION_DEPTH marks
- Award KEY_TERMINOLOGY marks if the student uses even one subject-specific term correctly
- Do NOT penalise simple language — reward clarity of thought"""
    else:
        subject_note = """Subject-specific rules (science/maths):
- Reward correct use of formulas, units, and scientific terms
- Correct answer with wrong units loses KEY_TERMINOLOGY only, not CONCEPTUAL_ACCURACY
- Steps described in words count towards EXPLANATION_DEPTH
- Do NOT penalise for weak English"""

    prompt = f"""You are a fair and encouraging examiner grading a school student's answer.

Question: {question}
Maximum marks: {max_marks}
Student's answer: {student_answer}

Grade using ONLY this rubric:
{rubric_lines}

General rules:
- Do NOT deduct marks for spelling, grammar, or weak English
- Award partial marks for partial understanding
- Be lenient and age-appropriate — right idea in simple words still gets credit
- Never award more than the marks allocated per parameter
{subject_note}

Respond in EXACTLY this format, nothing else:
{response_format}
TOTAL: <sum>/{max_marks}
SUMMARY: <one specific encouraging sentence: exactly what to add to score full marks next time>"""

    try:
        raw = _call_gemini(prompt)
        return _parse_rubric_response(raw, max_marks)
    except HTTPException:
        raise
    except Exception as e:
        return 0, f"Evaluation failed: {str(e)}"


def _parse_rubric_response(text: str, max_marks: int) -> tuple:
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
            feedback_lines.append(f"Tip: {summary}")
        elif "|" in line and ":" in line:
            try:
                param_part, reason = line.split("|", 1)
                param_name = param_part.split(":")[0].strip().replace("_", " ").title()
                score_part = param_part.split(":")[1].strip()
                feedback_lines.append(f"{param_name} ({score_part}): {reason.strip()}")
            except (ValueError, IndexError):
                feedback_lines.append(line)

    return total_marks, "\n".join(feedback_lines)


def _overall_feedback(total: int, max_marks: int) -> str:
    if max_marks == 0:
        return "No marks available."
    pct = (total / max_marks) * 100
    if pct >= 90:
        return "Excellent! You have a strong grasp of this topic."
    if pct >= 75:
        return "Very good! A little more revision and you'll nail it."
    if pct >= 50:
        return "Good effort. Review the questions where you lost marks."
    return "Needs improvement. Re-study the topic and try again."
