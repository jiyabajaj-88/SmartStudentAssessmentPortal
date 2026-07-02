

from app.db import conn
from psycopg2.extras import RealDictCursor

WEAK_THRESHOLD = 0.60  # topics where score < 60% are marked as weak


def detect_and_save_weak_topics(practice_assessment_id: int, student_id: int):
    """
    Aggregates marks_awarded vs marks per topic for a completed practice
    assessment and upserts weak topics into student_weak_topics.

    Called automatically at the end of evaluate_submission() in
    ai_practice_service.py.
    """
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Aggregate scores grouped by topic
        # practice_questions.topic_id was backfilled from practice_assessments
        cur.execute(
            """
            SELECT
                pq.topic_id,
                t.name                        AS topic_name,
                t.subject,
                SUM(pa.marks_awarded)         AS earned,
                SUM(pq.marks)                 AS total
            FROM practice_answers pa
            JOIN practice_questions pq
                ON pa.practice_question_id = pq.practice_question_id
            JOIN topics t
                ON pq.topic_id = t.topic_id
            WHERE pa.practice_assessment_id = %s
              AND pq.topic_id IS NOT NULL
            GROUP BY pq.topic_id, t.name, t.subject
            """,
            (practice_assessment_id,),
        )
        topic_scores = cur.fetchall()

        if not topic_scores:
            return  # no topic-tagged questions, nothing to do

        for row in topic_scores:
            topic_id   = row["topic_id"]
            earned     = row["earned"] or 0
            total      = row["total"] or 0

            if total == 0:
                continue

            score_pct = earned / total

            if score_pct < WEAK_THRESHOLD:
                # Upsert: if this student+topic combo already exists,
                # update the score and assessment_id to the latest result
                cur.execute(
                    """
                    INSERT INTO student_weak_topics
                        (student_id, topic_id, assessment_id, score)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (student_id, topic_id)
                    DO UPDATE SET
                        score         = EXCLUDED.score,
                        assessment_id = EXCLUDED.assessment_id,
                        identified_at = NOW()
                    """,
                    (student_id, topic_id, practice_assessment_id, round(score_pct * 100, 2)),
                )
            else:
                # Student improved on this topic — remove it from weak topics
                cur.execute(
                    """
                    DELETE FROM student_weak_topics
                    WHERE student_id = %s AND topic_id = %s
                    """,
                    (student_id, topic_id),
                )

        conn.commit()

    except Exception:
        conn.rollback()
        # Don't raise — weak topic detection failing should NOT
        # break the evaluation response the student sees
    finally:
        cur.close()