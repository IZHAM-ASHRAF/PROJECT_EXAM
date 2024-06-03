import io
import fitz  # PyMuPDF
import openai
from google.cloud import vision
from fastapi import FastAPI, File, UploadFile, HTTPException, status
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
import re
import pyodbc
from datetime import datetime, timedelta
import jwt
from fastapi import Depends

# Set your OpenAI and Google Cloud Vision API keys here
openai.api_key = ''
google_api_key = ''

# Initialize the Google Cloud Vision client
client = vision.ImageAnnotatorClient(client_options={"api_key": google_api_key})

# Initialize FastAPI app
app = FastAPI()

# Allow CORS for all origins (adjust for your needs)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection parameters
server = 'MAHESHP\\SQLEXPRESS'
database = 'ExamEva'
username = 'admin'
password = 'Admin@123'
driver = '{ODBC Driver 17 for SQL Server}'

# JWT settings
SECRET_KEY = "b2b94a9ad58d165f742e1f35db111c8b6dc3898bd93c4535350bdb369b373023"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Models
class ScoreResponse(BaseModel):
    score: int

class AdminRegister(BaseModel):
    username: str
    password: str

class AdminLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# Database functions
def get_db_connection():
    conn = pyodbc.connect(
        f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}'
    )
    return conn

def get_admin(username: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, password FROM Admins WHERE username = ?", (username,))
    admin = cursor.fetchone()
    cursor.close()
    conn.close()
    return admin

def create_admin(username: str, password: str):
    hashed_password = pwd_context.hash(password)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Admins (username, password) VALUES (?, ?)", (username, hashed_password))
    conn.commit()
    cursor.close()
    conn.close()

def store_score_in_db(score: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Scores (score) VALUES (?)", (score,))
    conn.commit()
    cursor.close()
    conn.close()

# Authentication functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_admin(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    admin = get_admin(username=username)
    if admin is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin not found")
    return admin

# PDF processing functions
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
    questions_answers = re.findall(r'(\d+\.\d*[\s\S]+?)(?=\d+\.\d*|$)', text)
    qa_pairs = []
    for qa in questions_answers:
        parts = qa.strip().split('\n')
        if len(parts) >= 3:
            question_id = parts[0].strip()
            question = parts[1].strip()
            answer = ' '.join(parts[2:]).strip()
            marks = assign_marks(question_id)
            qa_pairs.append((question, answer, marks))
    return qa_pairs

def assign_marks(question_id: str) -> int:
    if question_id.startswith("1"):
        return 2
    elif question_id.startswith("2"):
        return 3
    elif question_id.startswith("3"):
        return 4
    else:
        return 1  # default mark for other patterns

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
    total_marks = 0
    obtained_marks = 0

    for question, extracted_answer, marks in qa_pairs:
        total_marks += marks
        print(f"Question: {question}")
        print(f"Extracted Answer: {extracted_answer}")
        correctness_check = check_answer_with_openai(question, extracted_answer)
        if "correct" in correctness_check.lower():
            obtained_marks += marks
        print(f"Correctness Check: {correctness_check}")
        print()

    score = int((obtained_marks / total_marks) * 100)
    return score


# Endpoints
@app.post("/register", response_model=Token)
async def register(admin: AdminRegister):
    if get_admin(admin.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    create_admin(admin.username, admin.password)
    access_token = create_access_token(data={"sub": admin.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/token", response_model=Token)
async def login(form_data: AdminLogin):
    db_admin = get_admin(form_data.username)
    if not db_admin or not verify_password(form_data.password, db_admin[1]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/get_score", response_model=ScoreResponse)
async def get_score(file: UploadFile = File(...), token: str = Depends(get_current_admin)):
    pdf_bytes = await file.read()
    extracted_text = extract_text_from_pdf(pdf_bytes)
    qa_pairs = extract_qa_pairs(extracted_text)
    score = check_answers(qa_pairs)
    store_score_in_db(score)
    return ScoreResponse(score=score)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
