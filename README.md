# Leskode SOW Generator (ScopePilot AI)

> **AI-Powered SOW Generation and Zoho Implementation Planning Platform**

ScopePilot AI automatically transforms client requirement documents (specifications, tenders, notes, call transcripts) into structured, audit-ready, enterprise-grade Statements of Work (SOWs) using the official **Leskode 17-Section Master Flow Template**.

---

## 🚀 Key Features

- **Document Ingestion & Multi-Format Parsing**:
  - Direct processing of `.pdf`, `.docx`, `.xlsx`, and `.txt` requirement files.
  - Automatic structure detection, heading hierarchy, and section segmentation.
- **AI Requirements Extraction & Traceability**:
  - LLM pipeline extracts line-item functional requirements with confidence scores.
  - Full source attribution linking requirements back to specific files and page excerpts.
  - Manual requirement creation and consultant review workflows (`Approved`, `Needs Review`, `Rejected`).
- **Zoho Module Architecture & Licensing**:
  - Pre-seeded catalogue across 15 core Zoho applications (CRM, Books, Inventory, Desk, Creator, People, Payroll, Analytics, Projects, Flow, Sign, etc.).
  - AI-driven module recommendations matching client requirements with license tier and custom development feasibility.
- **Scope Tasks Work Breakdown Structure (WBS)**:
  - Generates comprehensive implementation tasks categorized by Configuration, Customisation, Integration, Migration, Training, and Testing.
  - Tracks acceptance criteria, deliverables, dependencies, and effort estimates.
- **Automation & Workflow Matrix**:
  - Maps business objectives to automated workflows, blueprints, trigger conditions, timing, and exception handling logic.
- **System Integrations Architecture**:
  - Cross-module data flows (Zoho CRM ↔ Books, Books ↔ Inventory, People ↔ Payroll).
  - External API and IoT / hardware integrations (e.g., Weighbridge RS-232 / TCP-IP scale lock).
- **Client Clarification Engine**:
  - Identifies missing, ambiguous, or contradictory requirements.
  - Generates targeted clarification questions with suggested options and records client answers.
- **Contractual Assumptions, Exclusions & Risk Mitigation**:
  - Standardized commercial protections, out-of-scope delivery boundaries, and risk assessment matrices.
- **Scope Coverage Validation & Audit**:
  - Algorithmic gap analysis scoring coverage and detecting unmapped requirements before document export.
- **Official Leskode 17-Section SOW Export**:
  - Generates production-ready `.docx` documents strictly adhering to Leskode brand standards, locked legal wording, milestone tables, and sign-off signature blocks.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, Pydantic v2, `python-docx`
- **AI Engine**: Google Gemini API (`gemini-3.5-flash-lite` / `gemini-1.5-pro`), OpenAI, or Claude
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons
- **Database**: SQLite (local development) / PostgreSQL (production via Supabase)

---

## 📦 Project Structure

```text
├── backend/
│   ├── app/
│   │   ├── ai/            # Multi-provider LLM pipeline & heuristic engine
│   │   ├── api/routes/    # FastAPI routes (projects, requirements, modules, tasks, sow, etc.)
│   │   ├── core/          # Authentication & configuration
│   │   ├── db/            # SQLAlchemy models & database session
│   │   └── document/      # Document extraction & Leskode 17-section DOCX generator
│   ├── templates/         # Master DOCX template
│   ├── seed_master_template.py # Seeds master template and organizations
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/    # ProjectWorkspace, Dashboard, NewProjectModal, etc.
│   │   ├── api.ts         # Axios REST API client
│   │   └── types.ts       # TypeScript interfaces
│   ├── package.json
│   └── vite.config.ts
├── package.json           # Root workspace scripts
└── README.md
```

---

## ⚡ Quick Start

### 1. Prerequisites
- Node.js (v18+)
- Python (v3.11+)

### 2. Backend Setup

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and supply your GOOGLE_API_KEY (or OpenAI/Anthropic credentials)

# Seed master template
python seed_master_template.py

# Start FastAPI backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive API docs will be available at: `http://127.0.0.1:8000/api/docs`

### 3. Frontend Setup

From the repository root (or inside `frontend/`):

```bash
cd frontend
npm install
npm run dev
```
The web dashboard will be accessible at: `http://localhost:5173/`

---

## 📄 License & Attribution

Designed and maintained for **Leskode Technologies** Zoho Implementation Planning.
All rights reserved.
