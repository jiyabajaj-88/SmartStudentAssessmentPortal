from app.db import conn

def get_student_by_id(student_id):
    conn.rollback()
    cur=conn.cursor()

    cur.execute(
        """SELECT student_id, name, email, student_class, school
        FROM students
        WHERE student_id = %s
        """,
        (student_id,)
    )

    return cur.fetchone()

def create_student(name, student_class, email, school):
    conn.rollback()
    cur=conn.cursor()   

    cur.execute(
        """INSERT INTO students (name, student_class, email, school)    
           VALUES (%s, %s, %s, %s)
           """,
        (name, student_class, email, school)
    )

    conn.commit()

    return {"message": "Student created successfully"}  