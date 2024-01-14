import sqlite3
import random

def setup_database():
    """
    Creates database used for evaluation.
    """
    random.seed(1)
    con = sqlite3.connect("example.db")
    cur = con.cursor()

    student_details = []
    
    for student_id in range(1000001, 1000011):
        given_name = random.choice(['John', 'Jane', 'Alice', 'Bob', 'Charlie', 'Daisy', 'Ethan', 'Fiona', 'George', 'Hannah'])
        last_name = random.choice(['Doe', 'Smith', 'Brown', 'Davis', 'Evans', 'Foster', 'Green', 'Hill', 'Irvine'])
        age = random.randint(18, 25)
        gender = random.choice(['Male', 'Female'])
        student_details.append((student_id, given_name, last_name, age, gender))

    cur.execute('DROP TABLE IF EXISTS student_details')
    cur.execute('''
        CREATE TABLE student_details (
            student_id INTEGER PRIMARY KEY,
            given_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL
        )
    ''')
    cur.executemany('INSERT INTO student_details VALUES (?, ?, ?, ?, ?)', student_details)

    units = [
        'Psychology', 'Computing', 'Mathematics', 'Physics', 'Chemistry', 
        'Biology', 'Engineering', 'Medicine', 'Law', 'Art', 
        'History', 'Philosophy', 'Economics', 'Political Science'
    ]
    
    unit_enrolment = [(random.choice(range(1000001, 1000011)), random.choice(units)) for _ in range(50)]
    cur.execute('DROP TABLE IF EXISTS unit_enrolment')
    cur.execute('''
        CREATE TABLE unit_enrolment (
            student_id INTEGER,
            unit_title TEXT,
            FOREIGN KEY (student_id) REFERENCES student_details (student_id)
        )
    ''')
    cur.executemany('INSERT INTO unit_enrolment VALUES (?, ?)', unit_enrolment)

    grade_data = [(person_id, round(random.uniform(50, 100), 2)) for person_id in range(1000001, 1000011)]
    cur.execute('DROP TABLE IF EXISTS grade')
    cur.execute('''
        CREATE TABLE grade (
            student_id INTEGER,
            grade REAL,
            FOREIGN KEY (student_id) REFERENCES student_details (student_id)
        )
    ''')
    cur.executemany('INSERT INTO grade VALUES (?, ?)', grade_data)
    con.commit()
    con.close()