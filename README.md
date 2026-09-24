# Voice AI Agent — Patient Registration System

**Author & Developer:** Ammad Raza  
**Repository:** [https://github.com/Bullseye25/voice-ai-patient-registration](https://github.com/Bullseye25/voice-ai-patient-registration)  
**Role:** Voice AI / Conversational AI Engineer  
**Date:** September 24, 2026  

---

## 1. Project Overview

The **Voice AI Agent Patient Registration System** is an end-to-end conversational healthcare platform designed to automate patient demographic intake over a dialable U.S. telephone number. Built to mirror the warmth, adaptability, and accuracy of a human clinical intake coordinator, the system collects patient details, performs real-time field validation, confirms accuracy with the caller, persists records to a durable database surviving restarts, and exposes a clean, standardized RESTful API.

### Live Demo & Contact Information
* **Dialable U.S. Phone Number:** `[Provisioning in Progress / TBD]`
* **Live API Base URL:** `[Deployment URL / Local Tunnel TBD]`
* **Interactive API Documentation:** `http://localhost:8000/docs` (Swagger UI)

---

## 2. System Architecture

The solution is divided into distinct, decoupled tiers ensuring strict separation of concerns:

```
                      +-----------------------------+
                      |         Caller (PSTN)       |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |   Telephony & STT/TTS Layer |
                      |    (Vapi / Retell / Twilio) |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |  Conversational AI Agent    |
                      |   (LLM + Function Calling)  |
                      +--------------+--------------+
                                     |  HTTP Tool Calls / Webhook
                                     v
+-----------------------------------------------------------------------+
|                       Backend REST Web Service                        |
|                                                                       |
|  +--------------------+   +--------------------+   +---------------+  |
|  |  FastAPI Router    |-->| Pydantic Validator |-->| PatientService|  |
|  +--------------------+   +--------------------+   +-------+-------+  |
+------------------------------------------------------------|----------+
                                                             |
                                                             v
                                            +-------------------------------+
                                            |     Durable SQLite Database   |
                                            |   (WAL Mode, Server Survives) |
                                            +-------------------------------+
```

1. **Telephony & Speech Processing:** Ingests inbound audio, provides ultra-low-latency Speech-to-Text (STT) and human-like Text-to-Speech (TTS).
2. **Conversational Engine:** LLM powered by tailored prompt engineering, handling intent recognition, phonetic spell-outs, clarifications, and confirmation read-back.
3. **Backend Service Layer (FastAPI):** Enforces server-side validation on all mandatory and optional fields, processes partial updates, handles soft deletes, and returns uniform JSON response envelopes.
4. **Persistence Layer:** Durable SQLite relational database operating with Write-Ahead Logging (WAL) for rapid concurrent writes, schema constraints, and crash resilience.

---

## 3. Technology Stack & Technical Justifications

| Component | Technology | Technical Rationale & Trade-offs |
| :--- | :--- | :--- |
| **Backend Framework** | **FastAPI (Python 3.14)** | Modern, high-performance async framework with native OpenAPI schema generation and tight integration with Pydantic for validation. Minimal boilerplate allows rapid 3-hour iteration. |
| **Data Validation** | **Pydantic v2** | Enforces rigorous server-side validation rules (regex, date range checks, phone normalization, enum guards) independently of voice model interpretations. |
| **Persistence** | **SQLite (WAL mode) / SQLAlchemy** | Zero external infrastructure overhead for instant local setup; survives server restarts; supports full SQL relational queries and indexes. In production, seamlessly migrates to PostgreSQL. |
| **Voice & Telephony** | **Vapi / Retell AI** | Abstract low-level WebSockets and audio buffer synchronization, allowing direct focus on prompt tuning, conversational edge cases, and deterministic tool calls. |
| **Testing** | **pytest + HTTPX** | Provides end-to-end integration and unit testing of database models, input validation edge cases, and API envelopes. |

---

## 4. Patient Demographic Data Model

The platform enforces the U.S. healthcare standard minimum demographic dataset:

| Field | Type | Required | Constraints & Description |
| :--- | :--- | :---: | :--- |
| `patient_id` | UUID | Auto | Unique identifier (UUIDv4) |
| `first_name` | String | Yes | 1–50 characters, letters, hyphens, apostrophes |
| `last_name` | String | Yes | 1–50 characters, letters, hyphens, apostrophes |
| `date_of_birth` | Date | Yes | Valid past date, MM/DD/YYYY format |
| `sex` | Enum | Yes | `Male`, `Female`, `Other`, `Decline to Answer` |
| `phone_number` | String | Yes | Valid 10-digit U.S. phone number |
| `email` | String | No | Valid email format (RFC 5322) |
| `address_line_1` | String | Yes | Primary street address |
| `address_line_2` | String | No | Apartment, Suite, or Unit number |
| `city` | String | Yes | 1–100 characters |
| `state` | String | Yes | Valid 2-letter U.S. state abbreviation |
| `zip_code` | String | Yes | 5-digit U.S. ZIP or ZIP+4 |
| `insurance_provider` | String | No | Insurance company name |
| `insurance_member_id`| String | No | Member / subscriber ID |
| `preferred_language` | String | No | Default: `English` |
| `emergency_contact_name` | String | No | Full contact name |
| `emergency_contact_phone`| String | No | Valid 10-digit U.S. phone number |
| `created_at` | Timestamp | Auto | UTC creation timestamp |
| `updated_at` | Timestamp | Auto | UTC update timestamp |
| `deleted_at` | Timestamp | Auto | Soft deletion timestamp (null if active) |

---

## 5. API Reference & Standards

All responses strictly follow a unified envelope format:

```json
{
  "data": { ... },
  "error": null
}
```

Error responses return:
```json
{
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Detailed error message",
    "details": []
  }
}
```

### Endpoints:
* `GET /patients`: List active patients. Query filters: `?last_name=`, `?date_of_birth=`, `?phone_number=`
* `GET /patients/{patient_id}`: Retrieve a single patient by UUID.
* `POST /patients`: Register a new patient (server-side validated). Returns `201 Created`.
* `PUT /patients/{patient_id}`: Partially or fully update existing patient records. Returns `200 OK`.
* `DELETE /patients/{patient_id}`: Soft-delete patient record (populates `deleted_at`). Returns `200 OK`.

---

## 6. Local Setup & Execution Guide

### Prerequisites
* Python 3.10+ (tested on Python 3.14)
* Git

### Installation
1. **Clone the repository:**
   ```bash
   git clone https://github.com/Bullseye25/voice-ai-patient-registration.git
   cd voice-ai-patient-registration
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your provider credentials
   ```

5. **Run Database Migrations & Start Server:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

6. **Run Automated Test Suite:**
   ```bash
   pytest -v
   ```

---

## 7. Trade-offs & Known Limitations

1. **Database Selection (SQLite vs. PostgreSQL):**
   * *Decision:* SQLite was chosen for portability, zero-dependency local execution, and resilience across server restarts within the 3-hour constraint.
   * *Production Roadmap:* In an enterprise multi-node environment, migration to PostgreSQL with connection pooling (e.g. PgBouncer) and row-level security is recommended.
2. **Audio Latency vs. LLM Reasoning Depth:**
   * *Decision:* Using streaming LLM tokens with fast models (e.g., GPT-4o-mini or Groq Llama-3) to keep time-to-first-audio under 800ms while maintaining clinical extraction accuracy.
3. **HIPAA & Compliance:**
   * *Scope:* As specified in the assessment guidelines, this prototype uses synthetic test data. Production implementation would mandate BAA with all vendors, KMS encryption at rest, TLS 1.3 in transit, and role-based access control (RBAC).

---

## 8. Author & Developer
* **Engineer:** Ammad Raza  
* **Email:** ammadraza27@gmail.com  
* **GitHub:** [Bullseye25](https://github.com/Bullseye25)
