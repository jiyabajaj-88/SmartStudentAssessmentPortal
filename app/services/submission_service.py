from app.db import conn

def create_submission(student_id, assessment_id):
       conn.rollback()
       cur=conn.cursor()
       cur.execute("""INSERT INTO submissions (student_id,assessment_id,status) 
                    VALUES (%s, %s, %s)
                    RETURNING submission_id
                    """,        
                    (student_id, assessment_id, "Submitted")
                    )
       submission_id = cur.fetchone()[0]
       conn.commit()
       
       return{
           "submission_id": submission_id,
           "status": "Submitted"
           
       }

def get_submission_by_id(submission_id):
    cur = conn.cursor()
    cur.execute("""SELECT * FROM submissions
                WHERE submission_id = %s
                """, 
                (submission_id,)
                )
    
    submission = cur.fetchone()
    conn.commit()
    return submission