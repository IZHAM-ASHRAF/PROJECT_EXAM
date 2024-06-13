-- Create table for course type
CREATE TABLE CourseType (
    CourseTypeId INT PRIMARY KEY IDENTITY(1,1),
    CourseTypeName VARCHAR(100) NOT NULL
);

-- Create table for courses
CREATE TABLE Course (
    CourseId INT PRIMARY KEY IDENTITY(1,1),
    CourseCode VARCHAR(50) NOT NULL,
    CourseName VARCHAR(100) NOT NULL,
    CourseTypeId INT FOREIGN KEY REFERENCES CourseType(CourseTypeId)
);

CREATE TABLE Year (
    YearId INT PRIMARY KEY IDENTITY(1, 1),
    YearName VARCHAR(50) NOT NULL
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

CREATE TABLE students (
    id INT PRIMARY KEY IDENTITY(1,1),
    student_id NVARCHAR(50) NOT NULL,
    name NVARCHAR(255) NOT NULL,
    semester_id INT NOT NULL,
    YearId INT NOT NULL,
    subject_id INT NOT NULL,
    Email NVARCHAR(255) NOT NULL,
    FOREIGN KEY (semester_id) REFERENCES Semester(SemesterId),
    FOREIGN KEY (subject_id) REFERENCES Subject(SubjectId),
    FOREIGN KEY (YearId) REFERENCES Year(YearId),
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