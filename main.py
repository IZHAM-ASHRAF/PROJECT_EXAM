import pyodbc
from fastapi import FastAPI, HTTPException, status, File, UploadFile, Form
from pydantic import BaseModel
from typing import List
import fitz  # PyMuPDF
import re
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

# Pydantic models
class User(BaseModel):
    email: str
    role: str

class Marks(BaseModel):
    student_id: str
    subject_name: str
    marks: int

class ScoreResponse(BaseModel):
    score: int

class Student(BaseModel):
    student_id: str
    name: str
    course_id: int

class Course(BaseModel):
    course_code: str
    course_name: str

class Subject(BaseModel):
    course_id: int
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
async def login(email: str, password: str):
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

@app.get("/admin/student_marks/{student_id}", response_model=List[Marks])
async def get_student_marks(student_id: str):
    conn = pyodbc.connect(DATABASE_CONNECTION_STRING)
    cursor = conn.cursor()
    cursor.execute("SELECT subject_name, marks FROM marks WHERE student_id = ?", (student_id,))
    marks = cursor.fetchall()
    conn.close()

    if not marks:
        raise HTTPException(status_code=404, detail="Student or marks not found")

    return [{"student_id": student_id, "subject_name": mark[0], "marks": mark[1]} for mark in marks]

@app.get("/admin/students", response_model=List[Student])
async def get_all_students():
    conn = pyodbc.connect(DATABASE_CONNECTION_STRING)
    cursor = conn.cursor()
    cursor.execute("SELECT student_id, name, course_id FROM students ORDER BY student_id ASC")
    students = cursor.fetchall()
    conn.close()

    return [{"student_id": student[0], "name": student[1], "course_id": student[2]} for student in students]

@app.post("/admin/upload_answersheet", response_model=List[Marks])
async def upload_answersheet(
    file: UploadFile = File(...),
    student_id: str = Form(...),
    subject_name: str = Form(...),
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
    cursor.execute("INSERT INTO marks (student_id, subject_name, marks) VALUES (?, ?, ?)", (student_id, subject_name, marks))
    conn.commit()

    cursor.execute("SELECT subject_name, marks FROM marks WHERE student_id = ?", (student_id,))
    student_marks = cursor.fetchall()
    conn.close()

    return [{"student_id": student_id, "subject_name": mark[0], "marks": mark[1]} for mark in student_marks]

@app.post("/admin/courses", response_model=Course)
async def create_course(course: Course):
    conn = pyodbc.connect(DATABASE_CONNECTION_STRING)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO courses (course_code, course_name) VALUES (?, ?)", (course.course_code, course.course_name))
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
    cursor.execute("INSERT INTO subjects (course_id, subject_name) VALUES (?, ?)", (subject.course_id, subject.subject_name))
    conn.commit()
    conn.close()
    return subject

@app.post("/admin/add_student", response_model=Student)
async def add_student(student: Student):
    conn = pyodbc.connect(DATABASE_CONNECTION_STRING)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO students (student_id, name, course_id) VALUES (?, ?, ?)", (student.student_id, student.name, student.course_id))
    conn.commit()
    conn.close()
    return student

@app.get("/admin/subjects", response_model=List[Subject])
async def get_all_subjects():
    conn = pyodbc.connect(DATABASE_CONNECTION_STRING)
    cursor = conn.cursor()
    cursor.execute("SELECT course_id, subject_name FROM subjects")
    subjects = cursor.fetchall()
    conn.close()

    return [{"course_id": subject[0], "subject_name": subject[1]} for subject in subjects]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
