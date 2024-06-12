import pyodbc
from fastapi import FastAPI, HTTPException, status, File, UploadFile, Form
from pydantic import BaseModel
from typing import List
import fitz  # PyMuPDF
import re
from typing import Optional
import openai
from google.cloud import vision
from fastapi.middleware.cors import CORSMiddleware

# Set your OpenAI and Google Cloud Vision API keys here
openai.api_key = ''
google_api_key = ''

# Initialize the Google Cloud Vision client
client = vision.ImageAnnotatorClient(client_options={"api_key": google_api_key})

app = FastAPI()

# Allow CORS for all origins (adjust for your needs)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
SERVER_NAME = 'MAHESHP\SQLEXPRESS'
DATABASE_NAME = 'ExamEva'
DATABASE_CONNECTION_STRING = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'


def fetch_all(query, params):
    conn = pyodbc.connect(DATABASE_CONNECTION_STRING)
    cursor = conn.cursor()
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    return results


# Pydantic models
class User(BaseModel):
    email: str
    role: str

class Marks(BaseModel):
    student_id: str
    subject_id: int
    marks: int

class Year(BaseModel):
    year_name: str

class Student(BaseModel):
    student_id: str
    name: str
    semester_id: int
    subject_id: int
    year_id: int
    email: str

class DetailedStudent(BaseModel):
    student_id: str
    name: str
    course_name: str
    semester_name: str
    course_type_name: str
    year_name: str
    subject_id: int
    subject_name: str
    marks: Optional[str] = None


class DetailedMarks(BaseModel):
    student_name: str
    subject_name: str
    marks: int
    year_name: str
    course_name: str

class Semester(BaseModel):
    semester_name: str
    course_id: int

class CourseType(BaseModel):
    course_type_name: str

class ScoreResponse(BaseModel):
    score: int

class Course(BaseModel):
    course_code: str
    course_name: str
    course_type_id: int

class Subject(BaseModel):
    semester_id: int
    subject_name: str

# Utility functions
def get_user(email: str):
    conn = pyodbc.connect(DATABASE_CONNECTION_STRING)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return {"email": user[1], "password": user[2], "role": user[3]}
    return None

def authenticate_user(email: str, password: str):
    user = get_user(email)
    if not user:
        return False
    if user["password"] == password:
        return user
    return False

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    pdf_document = fitz.open("pdf", pdf_bytes)
    full_text = ""

    for page_number in range(len(pdf_document)):
        page = pdf_document.load_page(page_number)
        image_bytes = page.get_pixmap().tobytes()
        image = vision.Image(content=image_bytes)
        feature = vision.Feature(type_=vision.Feature.Type.TEXT_DETECTION)
        request = {"image": image, "features": [feature]}

        try:
            response = client.annotate_image(request)
            texts = response.text_annotations
            if texts:
                full_text += texts[0].description
        except Exception as e:
            print(f"Error during API request for page {page_number + 1}: {e}")
            continue

    pdf_document.close()
    return full_text

def extract_qa_pairs(text: str):
    questions_answers = re.findall(r'(\d+\.\d+[\s\S]+?)(?=\d+\.\d+|$)', text)
    qa_pairs = []
    for qa in questions_answers:
        parts = qa.strip().split('\n')
        if len(parts) >= 3:
            question = parts[1].strip()
            answer = ' '.join(parts[2:]).strip()
            qa_pairs.append((question, answer))
    return qa_pairs

def check_answer_with_openai(question, extracted_answer):
    prompt = f"Question: {question}\nExtracted Answer: {extracted_answer}\nIs the extracted answer correct? If not, provide the correct answer."
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message['content'].strip()

def check_answers(qa_pairs):
    total_questions = len(qa_pairs)
    correct_answers = 0

    for question, extracted_answer in qa_pairs:
        print(f"Question: {question}")
        print(f"Extracted Answer: {extracted_answer}")
        correctness_check = check_answer_with_openai(question, extracted_answer)
        if "correct" in correctness_check.lower():
            correct_answers += 1
        print(f"Correctness Check: {correctness_check}")
        print()

    score = int((correct_answers / total_questions) * 100)
    return score

# Routes
@app.post("/login", response_model=User)
async def login(email: str = Form(...), password: str = Form(...)):
    user = authenticate_user(email, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    return user

@app.post("/register")
async def register(email: str, password: str, role: str):
    conn = pyodbc.connect(DATABASE_CONNECTION_STRING)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (email, password, role) VALUES (?, ?, ?)", (email, password, role))
    conn.commit()
    conn.close()
    return {"message": "User registered successfully"}


@app.get("/admin/students", response_model=List[DetailedStudent])
async def get_all_students():
    query = """
        SELECT s.student_id, s.name, sem.SemesterName, c.CourseName, ct.CourseTypeName, y.YearName, sub.SubjectName, sub.SubjectId, m.Marks
        FROM Students s
        JOIN Semester sem ON s.semester_id = sem.SemesterId
        JOIN Course c ON sem.CourseId = c.CourseId
        JOIN CourseType ct ON c.CourseTypeId = ct.CourseTypeId
        JOIN Year y ON s.YearId = y.YearId
        LEFT JOIN Subject sub ON s.subject_id = sub.SubjectId
        LEFT JOIN Marks m ON s.student_id = m.StudentId AND s.subject_id = m.SubjectId
        ORDER BY s.student_id ASC
        """

    students = fetch_all(query, ())
    detailed_students = []
    for student in students:
        student_id, name, semester_name, course_name, course_type_name, year_name, subject_name, subject_id, marks = student
        # Convert marks to string if it's not None
        marks_str = str(marks) if marks is not None else "N/A"
        detailed_student = DetailedStudent(
            student_id=student_id,
            name=name,
            semester_name=semester_name,
            course_name=course_name,
            course_type_name=course_type_name,
            year_name=year_name,
            subject_name=subject_name if subject_name else "N/A",
            subject_id=subject_id,
            marks=marks_str
        )
        detailed_students.append(detailed_student)
    return detailed_students

@app.get("/admin/student_marks/{student_id}/details", response_model=List[DetailedMarks])
async def get_student_marks_details(student_id: str):
    # Step 1: Fetch the marks for the student
    marks_query = """
        SELECT Marks, SubjectId
        FROM Marks
        WHERE StudentId = ?
        """
    marks = fetch_all(marks_query, (student_id,))

    # Step 2: Fetch additional details for each mark
    detailed_marks = []
    for mark in marks:
        subject_id = mark[1]
        subject_query = """
            SELECT sub.SubjectName, sem.SemesterId, c.CourseId
            FROM Subject sub
            JOIN Semester sem ON sub.SemesterId = sem.SemesterId
            JOIN Course c ON sem.CourseId = c.CourseId
            WHERE sub.SubjectId = ?
            """
        subject_details = fetch_all(subject_query, (subject_id,))

        # Only one result is expected
        if subject_details:
            subject_detail = subject_details[0]
            subject_name = subject_detail[0]
            semester_id = subject_detail[1]
            course_id = subject_detail[2]

            # Fetch course details
            course_query = """
                SELECT CourseName
                FROM Course
                WHERE CourseId = ?
                """
            course_details = fetch_all(course_query, (course_id,))
            course_name = course_details[0][0] if course_details else "Unknown"

            # Fetch year details using the student's year ID
            year_query = """
                SELECT y.YearName
                FROM Students s
                JOIN Year y ON s.YearId = y.YearId
                WHERE s.student_id = ?
                """
            year_details = fetch_all(year_query, (student_id,))
            year_name = year_details[0][0] if year_details else "Unknown"

            detailed_marks.append({
                "student_name": student_id,  # Since StudentId is not a foreign key, use student_id directly
                "subject_name": subject_name,
                "marks": mark[0],
                "year_name": year_name,
                "course_name": course_name
            })

    if not detailed_marks:
        raise HTTPException(status_code=404, detail="Marks not found for the student")

    return detailed_marks

@app.get("/user/students/{email}", response_model=List[DetailedStudent])
async def get_student_by_email(email: str):
    query = """
        SELECT s.student_id, s.name, sem.SemesterName, c.CourseName, ct.CourseTypeName, y.YearName, sub.SubjectName, sub.SubjectId, m.Marks
        FROM Students s
        JOIN Semester sem ON s.semester_id = sem.SemesterId
        JOIN Course c ON sem.CourseId = c.CourseId
        JOIN CourseType ct ON c.CourseTypeId = ct.CourseTypeId
        JOIN Year y ON s.YearId = y.YearId
        LEFT JOIN Subject sub ON s.subject_id = sub.SubjectId
        LEFT JOIN Marks m ON s.student_id = m.StudentId AND s.subject_id = m.SubjectId
        WHERE s.Email = ?
        ORDER BY s.student_id ASC
        """

    students = fetch_all(query, (email,))
    detailed_students = []
    for student in students:
        student_id, name, semester_name, course_name, course_type_name, year_name, subject_name, subject_id, marks = student
        marks_str = str(marks) if marks is not None else "N/A"
        detailed_student = DetailedStudent(
            student_id=student_id,
            name=name,
            semester_name=semester_name,
            course_name=course_name,
            course_type_name=course_type_name,
            year_name=year_name,
            subject_name=subject_name if subject_name else "N/A",
            subject_id=subject_id,
            marks=marks_str
        )
        detailed_students.append(detailed_student)
    return detailed_students

@app.post("/admin/upload_answersheet", response_model=List[Marks])
async def upload_answersheet(
        file: UploadFile = File(...),
        student_id: str = Form(...),
        subject_id: int = Form(...),
        email: str = Form(...)
):
    user = get_user(email)
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    pdf_bytes = await file.read()
    extracted_text = extract_text_from_pdf(pdf_bytes)
    qa_pairs = extract_qa_pairs(extracted_text)
    marks = check_answers(qa_pairs)

    conn = pyodbc.connect(DATABASE_CONNECTION_STRING)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO marks (StudentId, SubjectId, Marks) VALUES (?, ?, ?)", (student_id, subject_id, marks))
    conn.commit()

    cursor.execute("SELECT SubjectId, marks FROM marks WHERE StudentId = ?", (student_id,))
    student_marks = cursor.fetchall()
    conn.close()

    return [{"student_id": student_id, "subject_id": mark[0], "marks": mark[1]} for mark in student_marks]


@app.post("/admin/semesters", response_model=Semester)
async def add_semester(semester: Semester):
    conn = pyodbc.connect(DATABASE_CONNECTION_STRING)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Semester (SemesterName, CourseId) VALUES (?, ?)",
                   (semester.semester_name, semester.course_id))
    conn.commit()
    conn.close()
    return semester


@app.get("/admin/semesters", response_model=List[Semester])
async def get_all_semesters():
    conn = pyodbc.connect(DATABASE_CONNECTION_STRING)
    cursor = conn.cursor()
    cursor.execute("SELECT SemesterId, SemesterName, CourseId FROM Semester")
    semesters = cursor.fetchall()
    conn.close()

    return [{"semester_id": semester[0], "semester_name": semester[1], "course_id": semester[2]} for semester in
            semesters]


@app.post("/admin/coursetypes", response_model=CourseType)
async def add_course_type(course_type: CourseType):
    conn = pyodbc.connect(DATABASE_CONNECTION_STRING)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO CourseType (CourseTypeName) VALUES (?)", (course_type.course_type_name,))
    conn.commit()
    conn.close()
    return course_type


@app.post("/admin/years", response_model=Year)
async def add_year(year: Year):
    conn = pyodbc.connect(DATABASE_CONNECTION_STRING)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Year (YearName) VALUES (?)", (year.year_name,))
    conn.commit()
    conn.close()
    return year


@app.get("/admin/years", response_model=List[Year])
async def get_all_years():
    conn = pyodbc.connect(DATABASE_CONNECTION_STRING)
    cursor = conn.cursor()
    cursor.execute("SELECT YearId, YearName FROM Year")
    years = cursor.fetchall()
    conn.close()

    return [{"year_id": year[0], "year_name": year[1]} for year in years]


@app.get("/admin/coursetypes", response_model=List[CourseType])
async def get_all_course_types():
    conn = pyodbc.connect(DATABASE_CONNECTION_STRING)
    cursor = conn.cursor()
    cursor.execute("SELECT CourseTypeId, CourseTypeName FROM CourseType")
    course_types = cursor.fetchall()
    conn.close()

    return [{"course_type_id": course_type[0], "course_type_name": course_type[1]} for course_type in course_types]


@app.post("/admin/courses", response_model=Course)
async def create_course(course: Course):
    conn = pyodbc.connect(DATABASE_CONNECTION_STRING)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO course (CourseCode, CourseName, CourseTypeId) VALUES (?, ?, ?)",
                   (course.course_code, course.course_name, course.course_type_id))
    conn.commit()
    conn.close()
    return course


@app.get("/admin/courses", response_model=List[Course])
async def get_all_courses():
    conn = pyodbc.connect(DATABASE_CONNECTION_STRING)
    cursor = conn.cursor()
    cursor.execute("SELECT course_code, course_name FROM courses")
    courses = cursor.fetchall()
    conn.close()

    return [{"course_code": course[0], "course_name": course[1]} for course in courses]


@app.post("/admin/subjects", response_model=Subject)
async def create_subject(subject: Subject):
    conn = pyodbc.connect(DATABASE_CONNECTION_STRING)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO subject (SubjectName, SemesterId) VALUES (?, ?)",
                   (subject.subject_name, subject.semester_id))
    conn.commit()
    conn.close()
    return subject


@app.post("/admin/add_student", response_model=Student)
async def add_student(student: Student):
    conn = pyodbc.connect(DATABASE_CONNECTION_STRING)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO students (student_id, name, semester_id, subject_id, YearId, Email) VALUES (?, ?, ?, ?, ?, ?)",
                   (student.student_id, student.name, student.semester_id, student.subject_id, student.year_id, student.email))
    conn.commit()
    conn.close()
    return student

@app.get("/admin/dropdown_data")
async def get_dropdown_data():
    course_types_query = "SELECT CourseTypeId, CourseTypeName FROM CourseType"
    courses_query = "SELECT CourseId, CourseName FROM Course"
    semesters_query = "SELECT SemesterId, SemesterName FROM Semester"
    years_query = "SELECT YearId, YearName FROM Year"
    subjects_query = "SELECT SubjectId, SubjectName FROM Subject"

    course_types = fetch_all(course_types_query, ())
    courses = fetch_all(courses_query, ())
    semesters = fetch_all(semesters_query, ())
    years = fetch_all(years_query, ())
    subjects = fetch_all(subjects_query, ())

    dropdown_data = {
        "courseTypes": [{"id": ct[0], "name": ct[1]} for ct in course_types],
        "courses": [{"id": course[0], "name": course[1]} for course in courses],
        "terms": [{"id": sem[0], "name": sem[1]} for sem in semesters],
        "years": [{"id": year[0], "name": year[1]} for year in years],
        "subjects": [{"id": subj[0], "name": subj[1]} for subj in subjects]
    }

    return dropdown_data


@app.post("/admin/filter_data", response_model=List[DetailedStudent])
async def filter_data(filters: dict):
    course_type = filters.get("courseType")
    course = filters.get("course")
    term = filters.get("term")
    year = filters.get("year")
    subject = filters.get("subject")

    base_query = """
        SELECT s.student_id, s.Name, sem.SemesterName, c.CourseName, ct.CourseTypeName, y.YearName, sub.SubjectName, sub.SubjectId, m.Marks
        FROM Students s
        JOIN Semester sem ON s.semester_id = sem.SemesterId
        JOIN Course c ON sem.CourseId = c.CourseId
        JOIN CourseType ct ON c.CourseTypeId = ct.CourseTypeId
        JOIN Year y ON s.YearId = y.YearId
        LEFT JOIN Subject sub ON s.subject_id = sub.SubjectId
        LEFT JOIN Marks m ON s.student_id = m.StudentId AND s.subject_id = m.SubjectId
        WHERE 1=1
    """

    params = []

    if course_type:
        base_query += " AND ct.CourseTypeName = ?"
        params.append(course_type)
    if course:
        base_query += " AND c.CourseName = ?"
        params.append(course)
    if term:
        base_query += " AND sem.SemesterName = ?"
        params.append(term)
    if year:
        base_query += " AND y.YearName = ?"
        params.append(year)
    if subject:
        base_query += " AND sub.SubjectName = ?"
        params.append(subject)

    print("Generated SQL Query: ", base_query)
    print("With Parameters: ", params)

    students = fetch_all(base_query, params)
    detailed_students = []
    for student in students:
        student_id, name, semester_name, course_name, course_type_name, year_name, subject_name, subject_id, marks = student
        detailed_student = DetailedStudent(
            student_id=student_id,
            name=name,
            semester_name=semester_name,
            course_name=course_name,
            course_type_name=course_type_name,
            year_name=year_name,
            subject_name=subject_name if subject_name else "N/A",
            subject_id=subject_id,
            marks=str(marks) if marks is not None else "N/A"
        )
        detailed_students.append(detailed_student)
    return detailed_students

@app.get("/admin/subjects", response_model=List[Subject])
async def get_all_subjects():
    conn = pyodbc.connect(DATABASE_CONNECTION_STRING)
    cursor = conn.cursor()
    cursor.execute("SELECT SemesterId, SubjectName FROM subject")
    subjects = cursor.fetchall()
    conn.close()

    return [{"semester_id": subject[0], "subject_name": subject[1]} for subject in subjects]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
