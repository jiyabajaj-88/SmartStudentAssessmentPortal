from app.db import conn
import psycopg2
from  psycopg2.extras import RealDictCursor
def create_submission(student_id, assessment_id):
       conn.rollback()
       cur=conn.cursor(cursor_factory=RealDictCursor)
       cur.execute("""INSERT INTO submissions (student_id,assessment_id,status) 
                    VALUES (%s, %s, %s)
                    RETURNING submission_id, student_id, assessment_id, status, submitted_at
                    """,        
                    (student_id, assessment_id, "Submitted")
                    )
       submission = cur.fetchone()
       conn.commit()
       cur.close()
       
       return{
           "submission_id": submission["submission_id"],
           "student_id": submission["student_id"],
           "assessment_id": submission["assessment_id"],
           "status": submission["status"],
           "submitted_at": submission["submitted_at"],
       }

def get_submissions_by_student(student_id):
    conn.rollback()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """SELECT submission_id, student_id, assessment_id, status, submitted_at
        FROM submissions
        WHERE student_id = %s
        ORDER BY submitted_at DESC
        """,
        (student_id,),
    )
    submissions = cur.fetchall()
    cur.close()
    return submissions

def get_submission_by_id(submission_id):
    conn.rollback()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""SELECT * FROM submissions
                WHERE submission_id = %s
                """, 
                (submission_id,)
                )
    
    submission = cur.fetchone()
    cur.close()
    return submission