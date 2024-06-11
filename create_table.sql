-- Create table for course type
CREATE TABLE CourseType (
    CourseTypeId INT PRIMARY KEY IDENTITY(1,1),
    CourseTypeName VARCHAR(100) NOT NULL
);

CREATE TABLE Year (
    YearId INT PRIMARY KEY IDENTITY(1, 1),
    YearName VARCHAR(50) NOT NULL
);

-- Create table for courses
CREATE TABLE Course (
    CourseId INT PRIMARY KEY IDENTITY(1,1),
    CourseCode VARCHAR(50) NOT NULL,
    CourseName VARCHAR(100) NOT NULL,
    CourseTypeId INT FOREIGN KEY REFERENCES CourseType(CourseTypeId)
);

CREATE TABLE students (
    id INT PRIMARY KEY IDENTITY(1,1),
    student_id NVARCHAR(50) NOT NULL,
    name NVARCHAR(255) NOT NULL,
    semester_id INT NOT NULL,
    FOREIGN KEY (semester_id) REFERENCES Semester(SemesterId)
);

-- Create table for semesters
CREATE TABLE Semester (
    SemesterId INT PRIMARY KEY IDENTITY(1,1),
    SemesterName VARCHAR(50) NOT NULL,
    CourseId INT FOREIGN KEY REFERENCES Course(CourseId)
);

-- Create table for subjects
CREATE TABLE Subject (
    SubjectId INT PRIMARY KEY IDENTITY(1,1),
    SubjectName VARCHAR(100) NOT NULL,
    SemesterId INT FOREIGN KEY REFERENCES Semester(SemesterId)
);

-- Create table for student marks
CREATE TABLE Marks (
    MarkId INT PRIMARY KEY IDENTITY(1,1),
    StudentId VARCHAR(50) NOT NULL,
    SubjectId INT FOREIGN KEY REFERENCES Subject(SubjectId),
    Marks INT NOT NULL
);

CREATE TABLE users (
    id INT PRIMARY KEY IDENTITY(1,1),
    email NVARCHAR(255) NOT NULL,
    password NVARCHAR(255) NOT NULL,
    role NVARCHAR(50) NOT NULL
);


--CREATE TABLE marks (
--    id INT IDENTITY(1,1) PRIMARY KEY,
--    student_id INT,
--    subject_name NVARCHAR(255) NOT NULL,
--    marks INT,
--    FOREIGN KEY (student_id) REFERENCES students(id)
--);
--CREATE TABLE students (
--    id INT IDENTITY(1,1) PRIMARY KEY,
--    student_id NVARCHAR(50) UNIQUE NOT NULL,
--    name NVARCHAR(255) NOT NULL,
--    course_id INT,
--    FOREIGN KEY (course_id) REFERENCES courses(id)
--);
--CREATE TABLE courses (
--    id INT IDENTITY(1,1) PRIMARY KEY,
--    course_code NVARCHAR(50) UNIQUE NOT NULL,
--    course_name NVARCHAR(255) NOT NULL
--);
--CREATE TABLE users (
--    id INT IDENTITY(1,1) PRIMARY KEY,
--    email NVARCHAR(255) UNIQUE NOT NULL,
--    password NVARCHAR(255) NOT NULL,
--    role NVARCHAR(10) NOT NULL CHECK(role IN ('admin', 'student'))
--);
--
--CREATE TABLE subjects (
--    id INT IDENTITY(1,1) PRIMARY KEY,
--    course_id INT,
--    subject_name NVARCHAR(255) NOT NULL,
--    FOREIGN KEY (course_id) REFERENCES courses(id)
--);
