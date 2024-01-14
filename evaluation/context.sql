-- The student_details table contains personal and demographic information about students.
CREATE TABLE student_details (
    -- A unique identifier for each student. It is used as the primary key in this table.
    student_id INTEGER PRIMARY KEY,

    -- The given name or first name of the student i.e. John.
    given_name TEXT NOT NULL,

    -- The family name or last name of the student i.e. Smith.
    last_name TEXT NOT NULL,

    -- The age of the student i.e. how old the student is.
    age INTEGER NOT NULL,

    -- The gender of the student i.e. male or female.
    gender TEXT NOT NULL
);

-- The unit_enrolment table tracks which units students are enrolled in.
CREATE TABLE unit_enrolment (
    -- The student's identifier. This is a foreign key that references the student_id in the student_details table.
    student_id INTEGER,

    -- The title of the unit the student is enrolled in i.e. computing, english, math etc.
    unit_title TEXT,

    -- Establishes a foreign key relationship with the student_details table.
    FOREIGN KEY (student_id) REFERENCES student_details (student_id)
);

-- The grade table stores information about students' academic performance.
CREATE TABLE grade (
    -- The student's identifier, linking to the student_details table.
    student_id INTEGER,

    -- The mean grade of the student i.e. the mean grade of all units done by the student.
    grade REAL,

    -- A foreign key that links to the student_id in the student_details table.
    FOREIGN KEY (student_id) REFERENCES student_details (student_id)
);
