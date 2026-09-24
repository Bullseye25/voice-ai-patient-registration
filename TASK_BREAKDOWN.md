# Voice AI Agent — Patient Registration System
## Technical Task Breakdown & Engineering Execution Roadmap

**Document Author & Lead Developer:** Ammad Raza  
**Date:** September 24, 2026  
**Role:** Voice AI / Conversational AI Engineer  
**Project:** Voice-Based Patient Intake & Demographic Registration Platform  
**Target Completion Window:** 3 Hours Assessment Benchmark  

---

## 1. Executive Summary & System Architecture

### 1.1 Objective
Design, implement, and deploy a production-grade, conversational Voice AI Agent accessible via a real U.S. dialable telephone number. The system collects standard U.S. healthcare patient demographic information through natural language dialogue, enforces strict data validation server-side, persists records into a durable database surviving server restarts, and exposes a comprehensive RESTful API conforming to enterprise API standards.

### 1.2 System Architecture Diagram
```
+-------------------------------------------------------------------------+
|                              TELEPHONY LAYER                            |
|  Inbound PSTN Call -> Telephony Carrier (Twilio / Vapi / Retell AI)    |
|                                |                                        |
|                                v                                        |
|                   Speech-to-Text (STT) Engine                           |
|             (Deepgram Nova-2 / Whisper / Carrier STT)                   |
+-------------------------------------------------------------------------+
                                 |
                                 v
+-------------------------------------------------------------------------+
|                           CONVERSATIONAL LAYER                          |
|         Large Language Model (OpenAI GPT-4o / GPT-4o-mini)              |
|   - System Persona: CareCloud Intake Coordinator                        |
|   - Dynamic Intent Handling & Disambiguation                            |
|   - Spell-out & Clarification Logic (names, addresses)                  |
|   - Confirmation Read-back & Field Corrections                         |
|   - Function Calling / Tool Execution Layer                             |
+-------------------------------------------------------------------------+
                                 |
                                 v  (HTTP Webhook / Function Call)
+-------------------------------------------------------------------------+
|                           REST API SERVICE LAYER                        |
|                    FastAPI (Python 3.14) Web Service                    |
|   - Server-Side Pydantic v2 Validation (regex, date ranges, enums)     |
|   - Standardized Response Envelope: {"data": ..., "error": ...}         |
|   - Structured Logging & Observability Middleware                       |
|   - Endpoints: GET, POST, PUT, DELETE (Soft-Delete)                     |
+-------------------------------------------------------------------------+
                                 |
                                 v
+-------------------------------------------------------------------------+
|                              PERSISTENCE LAYER                          |
|                  SQLite / PostgreSQL Relational Database                |
|   - WAL Mode (Write-Ahead Logging) for concurrent access                |
|   - Strict Column Constraints, Indexes (phone_number, name)            |
|   - Soft Delete Handling (deleted_at IS NULL filters)                   |
|   - Seed Data & Schema Migration Management                             |
+-------------------------------------------------------------------------+
```

---

## 2. Patient Demographic Data Model Specifications

The database schema and validation engine must rigorously support the standard U.S. minimum healthcare demographic dataset:

| Field Name | Type | Validation & Formatting Rules | Required |
| :--- | :--- | :--- | :---: |
| `patient_id` | UUID | UUIDv4, Primary Key, Auto-generated | Auto |
| `first_name` | String | 1–50 characters, letters, hyphens, and apostrophes only | **Yes** |
| `last_name` | String | 1–50 characters, letters, hyphens, and apostrophes only | **Yes** |
| `date_of_birth` | Date | Valid date, past date only (not in future), MM/DD/YYYY format | **Yes** |
| `sex` | Enum | Allowed values: `Male`, `Female`, `Other`, `Decline to Answer` | **Yes** |
| `phone_number` | String | Valid 10-digit U.S. phone number (E.164 or normalized 10-digit) | **Yes** |
| `email` | String | RFC 5322 compliant email format | No |
| `address_line_1`| String | Valid street address (non-empty) | **Yes** |
| `address_line_2`| String | Apt, Suite, Unit, Building number | No |
| `city` | String | 1–100 characters, alphabetic + spaces | **Yes** |
| `state` | String | Valid 2-letter U.S. state abbreviation (e.g., CA, NY, TX) | **Yes** |
| `zip_code` | String | 5-digit U.S. ZIP or ZIP+4 (`^\d{5}(-\d{4})?$`) | **Yes** |
| `insurance_provider` | String | Insurance carrier name (e.g., Aetna, BCBS, UnitedHealthcare) | No |
| `insurance_member_id`| String | Alphanumeric subscriber / policy ID | No |
| `preferred_language` | String | Default: `English` | No |
| `emergency_contact_name` | String | Full name (letters, hyphens, spaces) | No |
| `emergency_contact_phone`| String | Valid 10-digit U.S. phone number | No |
| `created_at` | Timestamp | ISO 8601 UTC timestamp, auto-generated on record creation | Auto |
| `updated_at` | Timestamp | ISO 8601 UTC timestamp, auto-generated on modification | Auto |
| `deleted_at` | Timestamp | Nullable ISO 8601 UTC timestamp (used for soft deletion) | Auto |

---

## 3. Work Breakdown Structure (WBS) & Engineering Phases

### Phase 1: Project Setup, Repository & Standards Foundation
- [x] **Task 1.1: Challenge & Requirements Analysis**: Deep analysis of functional and non-functional requirements from the assessment specification.
- [x] **Task 1.2: Git Repository Initialization & Configuration**:
  - Initialize local git repository with `main` branch.
  - Configure production-grade `.gitignore` covering Python bytecode, virtual environments, `.env` secrets, SQLite databases, IDE artifacts, and OS cache files.
  - Set remote origin to `https://github.com/Bullseye25/voice-ai-patient-registration.git`.
- [x] **Task 1.3: Project Structure & Dependency Architecture**:
  - Define modular project structure:
    ```
    carecloud/
    ├── app/
    │   ├── __init__.py
    │   ├── main.py              # FastAPI application entrypoint & middleware
    │   ├── config.py            # Environment settings (Pydantic BaseSettings)
    │   ├── models/              # SQLAlchemy / SQLModel database models
    │   │   ├── __init__.py
    │   │   └── patient.py
    │   ├── schemas/             # Pydantic request/response schemas & validation
    │   │   ├── __init__.py
    │   │   └── patient.py
    │   ├── api/                 # REST API endpoints
    │   │   ├── __init__.py
    │   │   └── v1/
    │   │       ├── __init__.py
    │   │       ├── patients.py  # CRUD routes
    │   │       └── voice.py     # Telephony & webhook routes
    │   ├── services/            # Business logic layer
    │   │   ├── __init__.py
    │   │   └── patient_service.py
    │   └── core/                # Database engine, session, logging & utilities
    │       ├── __init__.py
    │       ├── database.py
    │       └── logger.py
    ├── tests/                   # Automated test suite (pytest)
    │   ├── __init__.py
    │   ├── conftest.py
    │   ├── test_models.py
    │   ├── test_api_patients.py
    │   └── test_voice_integration.py
    ├── prompts/                 # LLM system prompts & conversation design
    │   └── patient_intake_prompt.md
    ├── seed/                    # Demo seed data
    │   └── patients_seed.json
    ├── .env.example
    ├── .gitignore
    ├── README.md
    ├── requirements.txt
    └── TASK_BREAKDOWN.md
    ```
  - Formulate lightweight `requirements.txt` with locked dependencies (`fastapi`, `uvicorn`, `pydantic[email]`, `sqlalchemy`, `pytest`, `httpx`, `python-dotenv`).

---

### Phase 2: Data Modeling, Persistence & Validation Engine
- [x] **Task 2.1: Database Engine & Session Management**:
  - Implement SQLite database connection with connection pooling and WAL mode enabled (`PRAGMA journal_mode=WAL;`).
  - Implement declarative base and session dependency injection for FastAPI.
- [x] **Task 2.2: Patient Entity Definition (`app/models/patient.py`)**:
  - UUID primary key generation.
  - Indexed fields (`phone_number`, `last_name`, `date_of_birth`).
  - Soft-delete timestamp column (`deleted_at`).
  - Enums for `sex`.
- [x] **Task 2.3: Pydantic Validation Schemas (`app/schemas/patient.py`)**:
  - `PatientCreateSchema`: Strict validation rules (regex for names, 10-digit phone normalization, past-date DOB check, valid 2-letter state code, 5-digit ZIP).
  - `PatientUpdateSchema`: Support partial updates (`PATCH`/`PUT`) with all fields optional but validated if provided.
  - `PatientResponseSchema`: Response representation with ISO timestamps and UUIDs.
  - Standard API Envelope:
    ```json
    {
      "data": { ... },
      "error": null
    }
    ```
    and Error Envelope:
    ```json
    {
      "data": null,
      "error": {
        "code": "VALIDATION_ERROR",
        "message": "Validation failed for one or more fields",
        "details": [ ... ]
      }
    }
    ```
- [x] **Task 2.4: Seed Data Script**:
  - Create seed script to populate 2 realistic patient records for immediate reviewer demonstration and verification.

---

### Phase 3: REST API Service Layer Implementation
- [x] **Task 3.1: Service Layer (`app/services/patient_service.py`)**:
  - Clean separation of business logic from HTTP handlers.
  - Methods: `create_patient`, `get_patient_by_id`, `list_patients`, `update_patient`, `soft_delete_patient`, `find_by_phone`.
- [x] **Task 3.2: REST Endpoints (`app/api/v1/patients.py`)**:
  - `GET /patients`:
    - Filter query params: `?last_name=`, `?date_of_birth=`, `?phone_number=`
    - Automatically excludes soft-deleted patients (`deleted_at IS NULL`).
    - Returns HTTP 200 with standard envelope.
  - `GET /patients/{id}`:
    - Retrieve active patient by UUID.
    - Returns HTTP 200 or HTTP 404 with error envelope if not found or soft-deleted.
  - `POST /patients`:
    - Server-side validation of all mandatory demographic fields.
    - Returns HTTP 201 Created with created record.
    - Handles HTTP 400 / 422 with clear error details.
  - `PUT /patients/{id}`:
    - Updates existing patient record. Supports partial updates.
    - Returns HTTP 200 or HTTP 404 if not found.
  - `DELETE /patients/{id}`:
    - Performs soft deletion by stamping `deleted_at = datetime.utcnow()`.
    - Returns HTTP 200 confirming soft deletion.
- [x] **Task 3.3: Global Exception Handlers & Middleware**:
  - Uniform envelope formatting for 400, 404, 422, and 500 errors.
  - Request logging middleware capturing duration, status code, and endpoint.

---

### Phase 4: Comprehensive Automated Test Suite
- [x] **Task 4.1: Test Infrastructure (`tests/conftest.py`)**:
  - In-memory SQLite database or isolated test database for test runs.
  - Pytest fixtures for test client (`httpx.AsyncClient` or `starlette.testclient.TestClient`).
- [x] **Task 4.2: Unit & Integration Tests (`tests/test_api_patients.py`)**:
  - **Test Case 1**: Patient creation with valid data (returns 201 + UUID).
  - **Test Case 2**: Server-side validation failure on future DOB (returns 422).
  - **Test Case 3**: Server-side validation failure on invalid phone length / format (returns 422).
  - **Test Case 4**: Server-side validation failure on invalid state abbreviation (returns 422).
  - **Test Case 5**: Retrieval of existing patient by ID (returns 200).
  - **Test Case 6**: Query filtering by `phone_number`, `last_name`, and `date_of_birth`.
  - **Test Case 7**: Partial update of existing patient via PUT (returns 200 with modified fields).
  - **Test Case 8**: Soft delete functionality (returns 200; subsequent GET returns 404; database record retains `deleted_at`).
  - **Test Case 9**: Persistence test (data remains queryable after simulated service restart).

---

### Phase 5: Voice AI Agent & Telephony Architecture
- [x] **Task 5.1: Conversational Intake Flow Design & Prompt Engineering (`prompts/patient_intake_prompt.md`)**:
  - **Agent Persona**: Compassionate, clear, professional healthcare intake specialist.
  - **Required Intake Sequence**:
    1. Greeting: "Thank you for calling CareCloud Patient Registration. My name is Alex..."
    2. Collect: Full Name (First & Last). Clarify spelling if phonetic ambiguity exists.
    3. Collect: Date of Birth (MM/DD/YYYY). Reject future dates immediately with polite re-prompting.
    4. Collect: Sex (`Male`, `Female`, `Other`, `Decline to Answer`).
    5. Collect: Phone Number (10 digits).
    6. Collect: Residential Address (Street address, City, 2-letter State, 5-digit Zip).
    7. Opt-In for Optional Fields:
       *"I can also collect your insurance information, emergency contact, and preferred language. Would you like to provide any of those?"*
    8. Readback & Verification:
       *"Before I submit your registration, please let me confirm what I've recorded: [Full Summary]. Is everything accurate, or would you like to make any changes?"*
    9. Handling Corrections: Gracefully re-prompt and update any field caller corrects.
    10. Graceful Wrap-up: *"You're all set, [First Name]! Your patient registration is complete. Have a wonderful day!"*
- [x] **Task 5.2: LLM Tool Calling / Webhook Integration**:
  - Implement tool definitions:
    - `check_patient_exists(phone_number)` -> calls backend service to detect duplicates.
    - `create_patient_record(payload)` -> triggers `POST /patients`.
    - `update_patient_record(patient_id, payload)` -> triggers `PUT /patients/{id}`.
  - Webhook route: `POST /api/v1/voice/webhook` handling payload confirmation and returning structured voice responses.
- [x] **Task 5.3: Telephony Provider Provisioning**:
  - Configure dialable U.S. telephone number via voice platform (Vapi / Retell / Twilio).
  - Connect agent webhook to live backend endpoint (using secure public tunnel via `ngrok` or cloud deployment on Railway/Render).

---

### Phase 6: Edge Cases, Resilience & Bonus Features
- [x] **Task 6.1: Duplicate Caller Detection (Bonus)**:
  - When caller provides phone number (or from caller ID), check if record exists.
  - If existing patient found: *"It looks like we already have a record for [First Name] [Last Name]. Would you like to update your information instead?"*
- [x] **Task 6.2: Mid-Call Interruption & Correction Handling**:
  - Support mid-conversation corrections (e.g., "Actually, my last name is Davis, spelled D-A-V-I-S").
  - Support caller reset ("Can we start over from the beginning?").
- [x] **Task 6.3: Network / Database Failure Graceful Degradation**:
  - If database write fails during call, agent provides clear, polite message: *"I apologize, but our registration system is experiencing a temporary delay. Your details have been logged, and an intake coordinator will reach out to confirm."*
- [x] **Task 6.4: Observability & Audit Logging**:
  - Log complete conversation transcripts and extracted JSON payloads to stdout and rotating log files for post-call audit.

---

### Phase 7: Deployment, Documentation & Submission Deliverables
- [x] **Task 7.1: Professional `README.md`**:
  - Architecture overview & component breakdown.
  - Prerequisites and local setup guide.
  - Environment variables documentation.
  - Live phone number and API base URL.
  - cURL commands demonstrating each REST endpoint.
  - Technical trade-offs and rationale (e.g., SQLite vs Postgres, Vapi vs raw Twilio).
  - Next steps / future roadmap.
- [x] **Task 7.2: Git Push to GitHub**:
  - Remote repository verification (`https://github.com/Bullseye25/voice-ai-patient-registration.git`).
  - Clean commit history reflecting feature-by-feature progression.
- [x] **Task 7.3: End-to-End Live Verification**:
  - Live phone call test: Dial number, register sample patient, verify speech readback.
  - Database verification: Query SQLite database to verify persisted fields.
  - API verification: Query `GET /patients` and `GET /patients/{id}` to verify data integrity.
  - Repeat call test: Place second call to verify duplicate detection and persistence.

---

## 4. Priority Implementation Order: Getting Started

To maximize efficiency and guarantee a working, high-scoring submission within the evaluation parameters, implementation will proceed in the following strict order:

1. **Step 1: Foundational Scaffolding & Git Tracking (Immediate)**
   - Initialize git, configure `.gitignore`, create documentation (`README.md`, `TASK_BREAKDOWN.md`).
   - Push initial commit to GitHub repository.
2. **Step 2: Core Data Layer, Schema & Pydantic Validation (Feature 1)**
   - Build database connection, Patient SQLAlchemy model, and Pydantic validation schemas.
   - Implement comprehensive unit tests for validators (future date, 10-digit phone, state codes).
3. **Step 3: REST API Service Layer & Persistence (Feature 2)**
   - Implement `GET`, `POST`, `PUT`, `DELETE` (soft-delete) with standardized JSON envelope.
   - Run integration tests verifying persistence across server restarts.
4. **Step 4: Voice Agent Engine & Prompt Engineering (Feature 3)**
   - Author system prompt with conversational instructions, confirmation protocol, and tool calling schemas.
   - Connect voice webhook to local backend via tunnel.
5. **Step 5: Telephony Connection & End-to-End Live Testing (Feature 4)**
   - Provision live phone number, perform phone call intake test, verify database write and API query.
6. **Step 6: Bonus Features & Final Polish**
   - Implement duplicate detection by phone number.
   - Package README with live credentials, phone number, API URL, and submission notes.
