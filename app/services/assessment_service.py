from app.db import conn

def get_assessments_by_class(student_class):
    conn.rollback()
    cur=conn.cursor()
    
    cur.execute(
        """
        SELECT *
        FROM assessments
        WHERE class = %s
        """,
        (student_class,)
    )

    return cur.fetchall()

def get_assessment_by_id(assessment_id):
    conn.rollback()
    cur=conn.cursor()

    cur.execute(
        """SELECT * FROM assessments
        WHERE assessment_id = %s
        """,
        (assessment_id,)            
    )
    return cur.fetchone()
