# NitiSetu — Multilingual Civic Information Assistant

> **Tagline:** Bridging Citizens with Knowledge.
> **Current Version:** Phase 1 — Data Source Integration and Document Processing Foundation

---

## 1. Project Overview

**Problem Statement:**
NitiSetu is an AI-powered multilingual civic information assistant designed to help Indian citizens understand:
1. **Government Schemes & Eligibility:** Understand welfare benefits and evaluate personal eligibility criteria using deterministic rule evaluation.
2. **Indian Laws & Citizen Rights:** Retrieve statutory provisions, parliamentary acts, and consumer/privacy protections from official sources.
3. **Government Notices & Circulars:** Ingest official gazettes and PDFs uploaded by citizens, extracting text page-by-page.

NitiSetu is engineered so that citizens can ask questions in simple, everyday language and eventually receive understandable answers in English, Telugu (తెలుగు), and Hindi (हिन्दी).

---

## 2. Phase 1 Architecture & Three Data Sources

Phase 1 establishes three independent, decoupled information sources ready for future intent orchestration:

```
                                 ┌───────────────────────────────┐
                                 │     NitiSetu React Client     │
                                 │       (Vite + Tailwind)       │
                                 └───────────────┬───────────────┘
                                                 │
                                                 ▼
                                 ┌───────────────────────────────┐
                                 │      FastAPI Gateway v1       │
                                 │   (CORS / Middleware / Auth)  │
                                 └───────────────┬───────────────┘
                                                 │
             ┌───────────────────────────────────┼───────────────────────────────────┐
             │                                   │                                   │
             ▼                                   ▼                                   ▼
┌─────────────────────────┐         ┌─────────────────────────┐         ┌─────────────────────────┐
│        SOURCE A         │         │        SOURCE B         │         │        SOURCE C         │
│   NyayKosh Law Search   │         │ Verified Welfare Schemes│         │  Document Intelligence  │
│ (NeGD "Law as Code" API)│         │  & Deterministic Engine │         │  (PyMuPDF Page Parser)  │
└────────────┬────────────┘         └────────────┬────────────┘         └────────────┬────────────┘
             │                                   │                                   │
   ┌─────────┴─────────┐                         │                         ┌─────────┴─────────┐
   │                   │                         ▼                         │                   │
   ▼                   ▼                ┌─────────────────┐                ▼                   ▼
Live NeGD API     Mock Adapter          │  schemes.json   │          Local Secure       Page-by-Page
(Open Access)     (Dev Fallback)        │(5 Verified Acts)│          Upload Storage     Text Extraction
```

### Source A: NyayKosh — Real Law Retrieval
- Integrates with the official **NeGD (National e-Governance Division, MeitY)** "Law as Code" platform (`https://lawascode.negd.in/laac-api/v1`).
- Public read access is open and does not require an API key.
- Searches legislative acts, sections, and provisions (e.g. DPDP Act 2023, Consumer Protection Act 2019, Aadhaar Act 2016, IT Act 2000, RPwD Act 2016).
- If upstream government endpoints are unreachable or time out, the service transparently falls back to an isolated `NyayKoshMockAdapter`, clearly labeling `is_live_data: false`.

### Source B: Government Scheme Dataset & Deterministic Evaluator
- Contains five verified schemes derived from official government portals:
  1. **PM-KISAN** (Ministry of Agriculture and Farmers Welfare)
  2. **Ayushman Bharat PM-JAY** (National Health Authority, MoHFW)
  3. **PMAY-G** (Ministry of Rural Development)
  4. **NSP-CSSS** (Department of Higher Education, Ministry of Education)
  5. **Telangana Rythu Bandhu / Rythu Bharosa** (Department of Agriculture, Govt. of Telangana)
- Each scheme records verified benefits, eligibility criteria, exclusion rules, and required documents.
- Includes a **deterministic evaluation engine** that evaluates citizen answers condition-by-condition without LLM hallucination or premature government approvals.

### Source C: User-Uploaded PDFs — Document Intelligence
- Ingests government circulars, notices, and gazettes via `POST /api/v1/documents/upload`.
- Validates file extension (`.pdf`), MIME type (`application/pdf`), magic bytes (`%PDF-`), and file size (≤ 10 MB).
- Generates server-side UUIDs to prevent path traversal attacks.
- Uses **PyMuPDF** to extract text page-by-page while preserving 1-indexed page numbers.
- Detects scanned/image-only circulars and flags them as `OCR_REQUIRED`.

---

## 3. Technology Stack

### Frontend
- **Framework:** React 18
- **Build Tool:** Vite 6
- **Styling:** Tailwind CSS (Civic-tech palette)
- **Routing:** React Router DOM v6
- **HTTP Client:** Axios
- **Icons:** Lucide React

### Backend
- **Framework:** Python 3.10+ / FastAPI
- **ASGI Server:** Uvicorn
- **Data Validation & Settings:** Pydantic v2 & Pydantic-Settings
- **Document Processing:** PyMuPDF (`fitz`)
- **HTTP Client:** HTTPX (async client with timeout)
- **Testing:** Pytest & pytest-asyncio

---

## 4. Folder Structure

```
NitiSetu/
│
├── frontend/
│   ├── public/
│   │   └── vite.svg
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/
│   │   │   │   └── BackendStatusBadge.jsx
│   │   │   ├── documents/
│   │   │   │   └── DocumentUploadSection.jsx
│   │   │   ├── laws/
│   │   │   │   └── LawSearchSection.jsx
│   │   │   ├── layout/
│   │   │   │   ├── Header.jsx
│   │   │   │   └── Footer.jsx
│   │   │   └── schemes/
│   │   │       └── SchemeExplorerSection.jsx
│   │   ├── pages/
│   │   │   └── Home.jsx
│   │   ├── services/
│   │   │   └── api.js
│   │   ├── App.jsx
│   │   ├── index.css
│   │   └── main.jsx
│   ├── .env
│   ├── .env.example
│   ├── package.json
│   └── vite.config.js
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── chat.py
│   │   │   │   ├── document_routes.py
│   │   │   │   ├── health.py
│   │   │   │   ├── law_routes.py
│   │   │   │   └── scheme_routes.py
│   │   │   └── __init__.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── exceptions.py
│   │   ├── data/
│   │   │   └── schemes.json
│   │   ├── repositories/
│   │   │   ├── document_repository.py
│   │   │   └── scheme_repository.py
│   │   ├── schemas/
│   │   │   ├── common_schemas.py
│   │   │   ├── document_schemas.py
│   │   │   ├── law_schemas.py
│   │   │   └── scheme_schemas.py
│   │   ├── services/
│   │   │   ├── document_service.py
│   │   │   ├── eligibility_service.py
│   │   │   ├── nyaykosh_service.py
│   │   │   ├── pdf_extraction_service.py
│   │   │   └── scheme_service.py
│   │   ├── storage/
│   │   │   └── local_storage.py
│   │   └── main.py
│   ├── tests/
│   │   ├── test_document_routes.py
│   │   ├── test_health.py
│   │   ├── test_law_routes.py
│   │   ├── test_pdf_extraction.py
│   │   └── test_scheme_routes.py
│   ├── uploads/
│   ├── .env
│   ├── .env.example
│   └── requirements.txt
│
├── .gitignore
└── README.md
```

---

## 5. Prerequisites

- **Python:** v3.10+ (tested on Python 3.13)
- **Node.js:** v18+ (tested on Node v24)
- **npm:** v9+

---

## 6. Environment Configuration

### Backend (`backend/.env`)
```ini
PROJECT_NAME="NitiSetu API"
VERSION="1.1.0"
ENVIRONMENT="development"
API_V1_STR="/api/v1"

# CORS Allowed Origins
ALLOWED_ORIGINS="http://localhost:5173,http://127.0.0.1:5173"

# Source A: NyayKosh NeGD Law as Code API
NYAYKOSH_BASE_URL="https://lawascode.negd.in/laac-api/v1"
NYAYKOSH_API_KEY=""
NYAYKOSH_TIMEOUT_SECONDS=8.0

# Source B: Verified Scheme Dataset
SCHEMES_DATA_PATH="app/data/schemes.json"

# Source C: PDF Document Uploads
UPLOAD_DIRECTORY="uploads"
MAX_UPLOAD_SIZE_MB=10
```

### Frontend (`frontend/.env`)
```ini
VITE_API_BASE_URL=http://localhost:8000
```

---

## 7. Installation & Running Instructions

### Start the Backend
Open a terminal in `backend/`:
```powershell
# Windows PowerShell
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
```bash
# macOS / Linux
cd backend
python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- **OpenAPI Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Endpoint:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

### Start the Frontend
Open a second terminal in `frontend/`:
```bash
cd frontend
npm run dev
```

- **Web Application:** [http://localhost:5173](http://localhost:5173)

---

## 8. API Endpoint Documentation

### Source A: Laws & Rights (NyayKosh)
- `GET /api/v1/laws/search?q={query}`: Search Indian statutory provisions. Returns `is_live_data` indicating whether data came directly from NeGD or the mock adapter.

### Source B: Welfare Schemes
- `GET /api/v1/schemes`: List all 5 verified welfare schemes.
- `GET /api/v1/schemes/search?q={keyword}`: Search schemes by keyword.
- `GET /api/v1/schemes/{scheme_id}`: Retrieve full scheme details (benefits, rules, documents).
- `GET /api/v1/schemes/{scheme_id}/eligibility/questions`: Retrieve scheme-specific questionnaire.
- `POST /api/v1/schemes/{scheme_id}/eligibility/evaluate`: Deterministically evaluate applicant profile against scheme criteria.

### Source C: Document Intelligence
- `POST /api/v1/documents/upload`: Upload PDF (multipart/form-data). Returns page count and `processing_status` (`COMPLETED` or `OCR_REQUIRED`).
- `GET /api/v1/documents/{document_id}`: Get document metadata.
- `GET /api/v1/documents/{document_id}/pages`: Retrieve extracted text page-by-page.
- `DELETE /api/v1/documents/{document_id}`: Securely delete document and storage file.

### System & Health
- `GET /`: Discovery endpoint with module links.
- `GET /api/v1/health`: Service health check.
- `POST /api/v1/chat/test`: Development connectivity test endpoint.

---

## 9. How to Add or Update a Scheme Record

To add a new verified government scheme:
1. Open [backend/app/data/schemes.json](file:///d:/AGENTIC%20AI/NitiSetu/backend/app/data/schemes.json).
2. Append a verified JSON object with the required schema:
   ```json
   {
     "scheme_id": "NEW_SCHEME_ID",
     "scheme_name": "Official Scheme Name",
     "short_description": "Verified summary",
     "ministry": "Implementing Ministry",
     "target_beneficiaries": "Target group",
     "state_applicability": "All India or Specific State",
     "data_source": "verified_demo_dataset",
     "official_source_url": "https://official.gov.in/",
     "last_verified": "YYYY-MM-DD",
     "benefits": ["Benefit 1", "Benefit 2"],
     "eligibility_conditions": ["Condition 1"],
     "exclusion_conditions": ["Exclusion 1"],
     "required_documents": ["Document 1"]
   }
   ```
3. To configure deterministic eligibility evaluation, add the scheme's questionnaire in `EligibilityEvaluationService.SCHEME_QUESTIONNAIRES` and an evaluation method `_eval_<scheme_id>` in [backend/app/services/eligibility_service.py](file:///d:/AGENTIC%20AI/NitiSetu/backend/app/services/eligibility_service.py).

---

## 10. Automated Testing

Run the automated pytest suite (covers all routes, live NeGD mocking, deterministic eligibility, and PDF extraction):
```bash
python -m pytest backend/tests -v
```

**Results:** 24 passed in 2.52 seconds.

---

## 11. Strict Scope Boundaries & Current Limitations

- **No Full RAG or Embeddings Yet:** Text chunking, sentence embeddings, and ChromaDB vector indexing are intentionally deferred to Phase 2.
- **No LLM Chatbot:** Responses are deterministic; LLM intent classification will be added in Phase 2.
- **Scanned PDF OCR:** Image-only notices are identified as `OCR_REQUIRED`. OCR execution (Tesseract/PaddleOCR) is scheduled for subsequent phases.
- **Vernacular Translations:** The UI supports language selection, but dynamic machine translation of all content is slated for future phases.
