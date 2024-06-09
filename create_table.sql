--CREATE TABLE Marks (
--    id INT PRIMARY KEY IDENTITY,
--    student_id NVARCHAR(50),
--    course_id NVARCHAR(50),
--    subject_name NVARCHAR(100),
--    marks INT,
--    FOREIGN KEY (student_id) REFERENCES Students(student_id),
--    FOREIGN KEY (course_id) REFERENCES Courses(course_id)
--);
--
--CREATE TABLE Subjects (
--    subject_id INT PRIMARY KEY IDENTITY,
--    course_id NVARCHAR(50),
--    subject_name NVARCHAR(100) NOT NULL,
--    FOREIGN KEY (course_id) REFERENCES Courses(course_id)
--);
--
--CREATE TABLE Courses (
--    course_id NVARCHAR(50) PRIMARY KEY,
--    course_name NVARCHAR(100) NOT NULL
--);
--
---- Insert predefined courses
--INSERT INTO Courses (course_id, course_name) VALUES ('CP08', 'Course CP08');
--INSERT INTO Courses (course_id, course_name) VALUES ('CP01', 'Course CP01');
--INSERT INTO Courses (course_id, course_name) VALUES ('CP15', 'Course CP15');
--
--CREATE TABLE Admins (
--    id INT PRIMARY KEY IDENTITY,
--    username NVARCHAR(50) NOT NULL UNIQUE,
--    password NVARCHAR(255) NOT NULL
--);
--
--CREATE TABLE Students (
--    student_id NVARCHAR(50) PRIMARY KEY,
--    name NVARCHAR(100) NOT NULL,
--    password NVARCHAR(255) NOT NULL
--);
CREATE TABLE marks (
    id INT IDENTITY(1,1) PRIMARY KEY,
    student_id INT,
    subject_name NVARCHAR(255) NOT NULL,
    marks INT,
    FOREIGN KEY (student_id) REFERENCES students(id)
);
CREATE TABLE students (
    id INT IDENTITY(1,1) PRIMARY KEY,
    student_id NVARCHAR(50) UNIQUE NOT NULL,
    name NVARCHAR(255) NOT NULL,
    course_id INT,
    FOREIGN KEY (course_id) REFERENCES courses(id)
);
CREATE TABLE courses (
    id INT IDENTITY(1,1) PRIMARY KEY,
    course_code NVARCHAR(50) UNIQUE NOT NULL,
    course_name NVARCHAR(255) NOT NULL
);
CREATE TABLE users (
    id INT IDENTITY(1,1) PRIMARY KEY,
    email NVARCHAR(255) UNIQUE NOT NULL,
    password NVARCHAR(255) NOT NULL,
    role NVARCHAR(10) NOT NULL CHECK(role IN ('admin', 'student'))
);

CREATE TABLE subjects (
    id INT IDENTITY(1,1) PRIMARY KEY,
    course_id INT,
    subject_name NVARCHAR(255) NOT NULL,
    FOREIGN KEY (course_id) REFERENCES courses(id)
);
