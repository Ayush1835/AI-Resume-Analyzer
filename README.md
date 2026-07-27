# AI Resume Analyzer

AI Resume Analyzer is a production-ready, enterprise-grade full-stack web application designed to evaluate candidate resumes against target job descriptions. The system parses document files (PDF/DOCX), runs matching algorithms (evaluating hard skills, work experience spans, educational degrees, and keyword densities), and computes NLP semantic similarity using Sentence Transformers. It compiles feedback recommendations, integrates LLM options (Gemini/OpenAI), draws dynamic data analytics charts, and exports professional PDF audit reports.

---

## Key Features

1. **User Authentication**: Secure JWT session tokens (issued as HTTPOnly cookies and API headers), password hashing (bcrypt), and role management.
2. **Multi-Format Uploads**: Handles PDF (`pymupdf`/`pdfplumber`) and Word DOCX (`python-docx`) parsing.
3. **Capability Extraction**: Regex and Named Entity Recognition (spaCy) to parse contact info, education credentials, skills lists, and years of experience.
4. **Weighted ATS Score**: A weighted calculation (Skills 30%, Keywords 20%, Experience 20%, Education 10%, Formatting 10%, Completeness 10%).
5. **NLP Semantic Matching**: Computes sentence embeddings similarity using `all-MiniLM-L6-v2`. Features a reliable local TF-IDF cosine fallback if offline.
6. **Dual LLM Drivers**: Optional advanced suggestions from Gemini or OpenAI APIs, falling back to a structured rule-based NLP templates engine if no keys are set.
7. **Interactive Dashboard**: Features responsive Chart.js widgets representing candidates' matched skill frequencies.
8. **PDF Audit Report**: Compiles a ReportLab PDF detailing scorecard badges, missing requirements tables, and embedded matplotlib graphs.
9. **Admin Panel**: Administrator cockpit to monitor users, view platform uploads, inspect statistics, and manage records.

---

## Folder Structure

```
c:\Users\ayush\OneDrive\Desktop\RESUME.PROJECT2\
├── backend/
│   ├── app/
│   │   ├── database/
│   │   │   └── connection.py      # SQLite engines, session local, Base schema
│   │   ├── models/
│   │   │   └── models.py          # SQLAlchemy schemas (User, Resume, Analysis)
│   │   ├── schemas/
│   │   │   └── schemas.py         # Pydantic schemas (Token, AnalysisOut)
│   │   ├── services/
│   │   │   ├── auth_service.py    # BCrypt hashing, JWT encoders, Auth dependencies
│   │   │   ├── parser_service.py  # PDF/DOCX extractors, regex, and spaCy rules
│   │   │   ├── similarity_service.py # TF-IDF scoring, weights, semantic similarity
│   │   │   ├── ai_service.py      # Gemini/OpenAI drivers and fallback templates
│   │   │   └── pdf_service.py     # ReportLab layout engine, matplotlib plotter
│   │   ├── routers/
│   │   │   ├── auth.py            # Signup, login, logout endpoints
│   │   │   ├── resume.py          # PDF/DOCX uploads and parser triggers
│   │   │   ├── analysis.py        # ATS evaluations and PDF download endpoints
│   │   │   ├── admin.py           # Admin statistics and user management
│   │   │   └── views.py           # Jinja2 templates controllers
│   │   ├── templates/             # Jinja2 HTML layout pages
│   │   ├── static/                # Static CSS, JS main bundles
│   │   ├── uploads/               # Stored resumes (Git-ignored)
│   │   ├── reports/               # Stored PDF report downloads (Git-ignored)
│   │   └── temp/                  # Temp storage for parsing runs
│   ├── tests/                     # Pytest sandbox folder
│   │   ├── conftest.py            # In-memory SQLite fixtures
│   │   ├── test_auth.py           # User signups and profile assertions
│   │   ├── test_parser.py         # Contact info and date parsing tests
│   │   └── test_similarity.py     # ATS scoring math bounds verification
│   ├── requirements.txt           # PIP dependencies manifest
│   └── main.py                    # App entrypoint, DB init, admin seeding
└── README.md                      # Documentation file
```

---

## Installation & Setup

### Prerequisites
- Python 3.12+
- Pip package manager
- Internet connection (for initial installation and download of NLP packages)

### 1. Clone & Set Up Directory
Navigate to the root project folder `c:\Users\ayush\OneDrive\Desktop\RESUME.PROJECT2\backend` in your terminal.

### 2. Create Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Download spaCy Language Weights
To enable advanced entity name recognition, download the English package:
```powershell
python -m spacy download en_core_web_sm
```

### 5. Configure Environment Variables
Create a `.env` file in the `backend/` directory:
```env
SECRET_KEY=super-secret-cryptographic-hash-key-here-1234
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Database Url (defaults to local SQLite)
# DATABASE_URL=sqlite:///./resume_analyzer.db
# For production PostgreSQL:
# DATABASE_URL=postgresql://user:password@host:port/dbname

# Optional: Add LLM API Keys to unlock advanced AI feedback
GEMINI_API_KEY=your_gemini_api_key_here
# OPENAI_API_KEY=your_openai_api_key_here
```

### 6. Run Unit Tests
Verify that all system operations, text parsers, and JWT security gates compile successfully:
```powershell
pytest -v
```

### 7. Run the Application
Start the uvicorn server locally:
```powershell
python -m uvicorn main:app --reload
```
Once initialized, open `http://127.0.0.1:8000` in your web browser.

---

## API Documentation

FastAPI compiles interactive API documentation automatically using Swagger and ReDoc.
- **Swagger UI**: Visit `http://127.0.0.1:8000/docs` to test registration, upload operations, and admin commands.
- **ReDoc**: Visit `http://127.0.0.1:8000/redoc`.

---

## Seeding Defaults
On startup, the system checks the user registry database. If no administrator accounts exist, it seeds a default administrator account:
- **Email**: `admin@resumeanalyzer.com`
- **Password**: `AdminPass123!`
*Note: Make sure to log in as admin to test user oversight actions and inspect dashboard metrics.*

---

## Deployment Guidelines

### Docker Deployment
Build and run the application inside isolated Docker containers:

1. Create a `Dockerfile` under `backend/`:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm

COPY . .

# Expose FastAPI port
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

2. Build and run:
```powershell
docker build -t resume-analyzer .
docker run -p 8000:8000 --env-file .env resume-analyzer
```

### Render or Railway Cloud Deployments
- Set the repository root directory or the build command pointing to `backend/`.
- **Build Command**: `pip install -r requirements.txt && python -m spacy download en_core_web_sm`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Configure environment variables (`DATABASE_URL`, `SECRET_KEY`, `GEMINI_API_KEY`, etc.) inside the cloud hosting dashboard.

---

## Future Enhancements
- **LinkedIn Integration**: Imports profiles using OAuth2 connections.
- **GitHub Repository Analysis**: Connects to candidate profiles, parsing codebases to score coding projects.
- **Resume Versioning**: Enables side-by-side comparison of multiple versions to track score improvements.
