# Voice AI Agent — Patient Registration System

**Author & Developer:** Ammad Raza  
**Repository:** [https://github.com/Bullseye25/voice-ai-patient-registration](https://github.com/Bullseye25/voice-ai-patient-registration)  
**Role:** Voice AI / Conversational AI Engineer  
**Date:** September 24, 2026  

---

## 1. Project Overview

The **Voice AI Agent Patient Registration System** is an end-to-end conversational healthcare platform designed to automate patient demographic intake over a dialable U.S. telephone number. Built to mirror the warmth, adaptability, and accuracy of a human clinical intake coordinator, the system collects patient details, performs real-time field validation, confirms accuracy with the caller, persists records to a durable database surviving restarts, and exposes a clean, standardized RESTful API.

### Live Demo & Reviewer Contact Information
* **Dialable U.S. Phone Number:** `+1 (463) 223-1253` *(Call to speak with Alex, the Voice AI agent)*
* **Interactive Apple iOS Clinical Web Dashboard:** `http://127.0.0.1:8000/` *(Auto-launches in browser on start)*
* **Base API:** [https://carecloud-voice-ai.loca.lt](https://carecloud-voice-ai.loca.lt/)
* **Patients Endpoint:** [https://carecloud-voice-ai.loca.lt/patients](https://carecloud-voice-ai.loca.lt/patients)
* **Interactive API Docs (Swagger):** [https://carecloud-voice-ai.loca.lt/docs](https://carecloud-voice-ai.loca.lt/docs)
* **Voice Agent Webhook:** [https://carecloud-voice-ai.loca.lt/voice/webhook](https://carecloud-voice-ai.loca.lt/voice/webhook)

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

## 3. Technology Stack Alignment & Architecture Rationale

The platform strictly aligns with the assessment's recommended technology matrix, implementing the top industry standard at every tier:

| Layer | Assessment Recommendation | Implemented Technology | What It Does (In Simple Words) |
| :--- | :--- | :--- | :--- |
| **Telephony + Voice AI** | Vapi, Retell AI, Bland.ai, Twilio + Deepgram/ElevenLabs | **Vapi Telephony Trunk** (Deepgram Nova-2 + ElevenLabs Rachel) | **The Ears & Voice:** Answers the incoming phone call on `+1 (463) 223-1253`, turns the patient's spoken voice into text in real time, and speaks back in a realistic, empathetic human clinical voice. |
| **LLM Reasoning** | OpenAI GPT-4o / 4o-mini, Anthropic Claude, Gemini, Groq | **OpenAI `gpt-4o-mini`** (Managed via Vapi) | **The Brain:** Understands conversational dialogue, extracts patient details (name, DOB, address), asks for spelling clarifications, performs readback confirmation, and calls database tools. |
| **Backend Framework** | Node.js (Express), Python (FastAPI/Flask), Go, Rails | **Python (FastAPI)** + ASGI Uvicorn | **The Coordinator / Traffic Controller:** Handles inbound webhook requests from the voice agent, orchestrates business logic, processes REST API queries, and manages data flow. |
| **Data Validation** | Framework / Schema Validation | **Pydantic v2 Schemas** | **The Security Guard:** Enforces strict clinical data integrity (e.g., birth dates cannot be in the future, phones must be 10 digits, states must be valid 2-letter codes) before anything touches the database. |
| **Database & Persistence** | PostgreSQL, SQLite (for simplicity), MongoDB, **Supabase** | **Supabase Cloud PostgreSQL + Official Supabase Python SDK** *(with SQLite WAL local fallback)* | **The Filing Cabinet / Memory:** Permanently stores all registered patient records in an encrypted cloud database on AWS via both direct connection pooling and the official Supabase SDK, keeping them organized, searchable, and crash-resilient. |
| **Public Gateway / Tunnel** | Railway, Render, Fly.io, Vercel, ngrok | **Custom Branded Tunnel** (`carecloud-voice-ai.loca.lt`) + Cloudflare | **The Public Bridge:** Creates a secure public HTTPS address so Vapi's telephony servers in the cloud can reach the local backend without firewall issues. |
| **Automated Testing** | Standard Testing Suite | **pytest + HTTPX** (30/30 Tests Passing) | **The Quality Inspector:** Automatically executes 30 simulation tests across validation edge cases, database persistence across restarts, and voice webhook handling. |

---

## 4. LLM Architecture, Telephony Limits & Billing Model

### 4.1 LLM Selection: OpenAI `gpt-4o-mini`
* **Latency Optimization:** Real-time telephony requires immediate conversational response. `gpt-4o-mini` delivers sub-250ms Time-To-First-Token (TTFT), eliminating unnatural conversational pauses.
* **Deterministic Function Calling:** Guarantees strict JSON output conforming to Pydantic schemas when executing tools (`check_patient_by_phone`, `register_patient`, and `update_patient`).
* **Cost Efficiency:** Highly economical (\$0.15 / 1M input tokens, \$0.60 / 1M output tokens), making production scaling viable.
* **Interchangeability:** The architecture decouples the LLM provider; the Vapi assistant can switch instantly to Anthropic Claude 3.5 Sonnet, Google Gemini 1.5 Flash, or Groq Llama 3.3.

### 4.2 Telephony Limits & Safety Safeguards
* **Free Tier Credits:** Vapi provides \$10.00 in starter trial credits (equivalent to ~60 to 100+ minutes of live phone calls).
* **Concurrency:** Up to 10 concurrent active telephone calls supported simultaneously.
* **Call Safety Cap:** Maximum call duration is enforced at **10 minutes** (`maxDurationSeconds: 600`) to prevent runaway sessions.
* **Silence Timeout:** Automatically terminates the call if caller is silent for **30 seconds**.

### 4.3 Billing Model Breakdown
Vapi bills per second of active connected call time across 5 decoupled pipeline layers:

| Component | Provider Used | Rate / Minute | Description |
| :--- | :--- | :--- | :--- |
| **Vapi Platform Fee** | Vapi Orchestration | \$0.050 / min | Audio streaming, interruption handling, tool execution |
| **Speech-to-Text (STT)** | Deepgram Nova-2 | ~\$0.005 / min | Real-time speech transcription (<150ms latency) |
| **LLM Reasoning** | OpenAI GPT-4o-mini | ~\$0.010 / min | Intent parsing, conversation logic, function calling |
| **Text-to-Speech (TTS)** | ElevenLabs (Rachel) | ~\$0.030 / min | High-fidelity, natural clinical intake persona voice |
| **Telephony Carrier (PSTN)** | Vapi Inbound Phone | ~\$0.015 / min | Inbound cellular/landline phone connection |
| **TOTAL ESTIMATED COST** | **All Included** | **~\$0.09 – \$0.12 / min** | **Billed only while call is active (\$0 when idle)** |

* **Estimated Cost per Intake Call:** An average 1.5 to 2.5 minute registration call costs approximately **\$0.15 to \$0.25**, allowing 40–60+ complete registrations on standard trial credits.

---

## 5. Patient Demographic Data Model

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

### Endpoints & cURL Examples:

#### 1. List Active Patients (with Optional Filters)
```bash
# List all active patients
curl -X GET "https://carecloud-voice-ai.loca.lt/patients"

# Search by phone number
curl -X GET "https://carecloud-voice-ai.loca.lt/patients?phone_number=5551234567"

# Search by last name
curl -X GET "https://carecloud-voice-ai.loca.lt/patients?last_name=Vance"
```

#### 2. Register New Patient (POST /patients)
```bash
curl -X POST "https://carecloud-voice-ai.loca.lt/patients" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Jane",
    "last_name": "Doe",
    "date_of_birth": "05/14/1990",
    "sex": "Female",
    "phone_number": "555-234-5678",
    "email": "jane.doe@example.com",
    "address_line_1": "123 Main Street",
    "city": "Austin",
    "state": "TX",
    "zip_code": "78701",
    "insurance_provider": "Aetna",
    "preferred_language": "English"
  }'
```

#### 3. Retrieve Single Patient (GET /patients/:id)
```bash
curl -X GET "https://carecloud-voice-ai.loca.lt/patients/<patient_id>"
```

#### 4. Update Existing Patient (PUT /patients/:id)
```bash
curl -X PUT "https://carecloud-voice-ai.loca.lt/patients/<patient_id>" \
  -H "Content-Type: application/json" \
  -d '{
    "city": "Dallas",
    "phone_number": "555-888-9999"
  }'
```

#### 5. Soft-Delete Patient (DELETE /patients/:id)
```bash
curl -X DELETE "https://carecloud-voice-ai.loca.lt/patients/<patient_id>"
```

---

## 6. Reviewer Phone Call Testing Guide

Reviewers can call the live U.S. phone number directly:
* **Call Number:** `+1 (463) 223-1253`

### Suggested Test Scenarios:
1. **Scenario 1: Happy Path Registration**
   * Call the number.
   * State your First and Last Name when prompted.
   * Provide Date of Birth (e.g., *"May 14th, 1990"*).
   * State Sex (*"Female"* or *"Male"*).
   * Provide 10-digit Phone Number.
   * Provide Street Address, City, State, and Zip.
   * When asked if you wish to provide insurance or emergency contact, opt-in or say *"No thank you"*.
   * Listen to the AI read back all your information.
   * Confirm with *"Yes, that is correct"*.
   * The AI will finalize registration: *"You're all set, [Name]!"*
   * Query `GET /patients` on the API to verify your record is persisted!
     `https://carecloud-voice-ai.loca.lt/patients`

2. **Scenario 2: Error Handling & Correction Testing**
   * Try giving an invalid date (e.g. a future year like 2030) — the agent will politely re-prompt.
   * Try giving a 3-digit phone number — the agent will detect the short length and ask for 10 digits.
   * Spell out an uncommon last name (e.g., *"D-A-V-I-S"*) — the agent will confirm and record it.
   * Interrupt or correct a detail: *"Actually, my apartment number is 4B, not 4A"* — the agent updates it immediately.

3. **Scenario 3: Duplicate Detection (Bonus Challenge)**
   * Call back from the same phone number (or state the same phone number).
   * The agent will recognize your number: *"It looks like we already have a record for [First Name] [Last Name]. Would you like to update your information instead?"*

---

## 7. Local Setup & Execution Guide

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

## 8. Trade-offs & Known Limitations

1. **Database Selection (SQLite vs. PostgreSQL):**
   * *Decision:* SQLite was chosen for portability, zero-dependency local execution, and resilience across server restarts within the 3-hour constraint.
   * *Production Roadmap:* In an enterprise multi-node environment, migration to PostgreSQL with connection pooling (e.g. PgBouncer) and row-level security is recommended.
2. **Audio Latency vs. LLM Reasoning Depth:**
   * *Decision:* Using streaming LLM tokens with fast models (e.g., GPT-4o-mini or Groq Llama-3) to keep time-to-first-audio under 800ms while maintaining clinical extraction accuracy.
3. **HIPAA & Compliance:**
   * *Scope:* As specified in the assessment guidelines, this prototype uses synthetic test data. Production implementation would mandate BAA with all vendors, KMS encryption at rest, TLS 1.3 in transit, and role-based access control (RBAC).

---

## 9. Author & Developer
* **Engineer:** Ammad Raza  
* **Email:** ammadraza27@gmail.com  
* **GitHub:** [Bullseye25](https://github.com/Bullseye25)
