# BUGSLASH

### Multi-Language Intelligent Bug Detection, Verification & Automated Fixing System

BUGSLASH is a multi-language static analysis and verification platform designed to detect software defects across different programming languages, normalize analyzer output into a common model, verify findings with additional evidence, and provide a foundation for automated bug fixing.

It combines language-specific developer tooling with a unified FastAPI backend and React/TypeScript interface, allowing developers to analyze individual source files or complete project archives through one workflow.

> **Project status:** Production-deployed MVP  
> **Frontend:** Vercel · **Backend:** Render · **Database:** Neon PostgreSQL

---

## Why BUGSLASH?

Modern static-analysis tools are powerful, but each language ecosystem has its own tooling, output format, severity model, and execution workflow.

BUGSLASH provides a unified layer over those tools.

```text
Source Code / Project
        │
        ▼
Language Detection
        │
        ▼
Analyzer Selection
        │
        ├── Python       → Ruff
        ├── JavaScript   → ESLint
        ├── TypeScript   → ESLint
        ├── C / C++      → Clang-Tidy
        ├── Java         → SpotBugs / Maven
        ├── Go           → Staticcheck
        └── Rust         → Clippy
        │
        ▼
Finding Normalization
        │
        ▼
Verification
        │
        ▼
Unified Scan Result
        │
        ▼
Web Dashboard
```

The long-term system extends this pipeline with automated fixes, LLM-assisted explanations, GitHub integration, background jobs, and stronger sandboxing.

---

# Core Capabilities

## Multi-Language Analysis

BUGSLASH currently supports analysis workflows for:

| Language | Analyzer / Tool | Status |
|---|---|---|
| Python | Ruff | ✅ |
| JavaScript | ESLint | ✅ |
| TypeScript | ESLint | ✅ |
| C / C++ | Clang-Tidy | ✅ |
| Java | SpotBugs + Maven | ✅ |
| Go | Staticcheck | ✅ |
| Rust | Clippy | ✅ |

Each analyzer produces tool-specific output which is converted into BUGSLASH's common finding representation.

---

## Unified Finding Model

Instead of exposing every analyzer's proprietary output format to the frontend, BUGSLASH normalizes findings into a common structure.

```python
Finding(
    language="python",
    file="example.py",
    line=3,
    column=5,
    category="F841",
    severity="high",
    message="Local variable `unused` is assigned to but never used",
    analyzer="ruff",
    confidence=0.95,
)
```

This gives the frontend a consistent representation regardless of the underlying language or analyzer.

---

## Verification Layer

Detection and verification are treated as separate stages.

A finding may be detected by a static analyzer and then passed through a verification layer where additional evidence is collected.

For example, Python source is syntax-verified using Python's compilation machinery before the finding is classified.

```text
Analyzer Finding
      │
      ▼
Verification Engine
      │
      ├── Evidence
      ├── Verification status
      └── Confidence
      │
      ▼
Verified / Potential / Unverified Result
```

> Verification is intentionally evidence-based. A successful syntax check does not claim that runtime behavior is universally correct.

---

# System Architecture

```text
                         ┌──────────────────────┐
                         │       Developer      │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ React + TypeScript   │
                         │      Frontend        │
                         └──────────┬───────────┘
                                    │ HTTP / JSON
                                    ▼
                         ┌──────────────────────┐
                         │       FastAPI        │
                         │        API           │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   BUGSLASH Engine    │
                         │                      │
                         │ Language Detection   │
                         │ Analyzer Selection   │
                         │ Finding Normalization│
                         │ Verification         │
                         └──────────┬───────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │          │          │          │          │
              ▼          ▼          ▼          ▼          ▼
            Ruff      ESLint    Clang-Tidy  SpotBugs  Staticcheck
                                                       │
                                                       ▼
                                                     Clippy

                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   SQLAlchemy ORM     │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ PostgreSQL / Neon    │
                         │                      │
                         │ Projects             │
                         │ Scans                │
                         │ Findings             │
                         └──────────────────────┘
```

---

# Application Workflow

### 1. Upload

The user submits either:

- A single supported source file
- A ZIP archive containing a project

### 2. Language Detection

BUGSLASH determines the language from the source file extension and selects the appropriate analyzer.

### 3. Static Analysis

The selected analyzer executes against the source.

Examples:

```text
.py  → Ruff
.js  → ESLint
.ts  → ESLint
.cpp → Clang-Tidy
.java → SpotBugs
.go  → Staticcheck
.rs  → Clippy
```

### 4. Normalization

Analyzer-specific results are transformed into the common `Finding` model.

### 5. Verification

The verification subsystem collects additional evidence where a verifier is available.

### 6. Persistence

Completed scans and findings are stored in PostgreSQL.

### 7. Visualization

The React dashboard displays:

- Scan history
- Files analyzed
- Findings
- Severity
- Analyzer
- Verification status
- Confidence
- Source location
- Diagnostic message

---

# Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React |
| Frontend Language | TypeScript |
| Build Tool | Vite |
| Backend | FastAPI |
| Backend Language | Python |
| ORM | SQLAlchemy |
| Database | PostgreSQL |
| Hosted Database | Neon |
| Containerization | Docker |
| Deployment | Vercel + Render |
| Python Analysis | Ruff |
| JS/TS Analysis | ESLint |
| C/C++ Analysis | Clang-Tidy |
| Java Analysis | SpotBugs + Maven |
| Go Analysis | Staticcheck |
| Rust Analysis | Clippy |
| Version Control | Git + GitHub |
| API Testing | curl / HTTP |
| Frontend Testing | Vitest |
| Backend Testing | Pytest |

---

# Repository Structure

```text
BugSlash/
│
├── backend/
│   ├── analyzer_models/
│   │   ├── python_analyzer.py
│   │   ├── javascript_analyzer.py
│   │   ├── cpp_analyzer.py
│   │   ├── java_analyzer.py
│   │   ├── go_analyzer.py
│   │   └── rust_analyzer.py
│   │
│   ├── api/
│   │   └── main.py
│   │
│   ├── database/
│   │   ├── connection.py
│   │   ├── models.py
│   │   └── repository.py
│   │
│   ├── models/
│   │   └── finding.py
│   │
│   ├── verification/
│   │   ├── python_verifier.py
│   │   └── verification_engine.py
│   │
│   ├── engine.py
│   ├── language_detector.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .dockerignore
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── types/
│   │   └── ...
│   ├── package.json
│   └── vite.config.ts
│
├── .gitignore
└── README.md
```

---

# API

The FastAPI backend currently exposes the following core endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | API information |
| `GET` | `/health` | Health check |
| `POST` | `/analyze` | Analyze a single source file |
| `POST` | `/analyze-project` | Analyze a ZIP project |
| `GET` | `/scans` | Retrieve scan history |
| `GET` | `/scans/{scan_id}` | Retrieve scan details |

### Example

```bash
curl -X POST https://bugslash-backend.onrender.com/analyze \
  -F "file=@example.py"
```

Example response:

```json
{
  "file": "example.py",
  "language": "python",
  "findings": [
    {
      "language": "python",
      "file": "example.py",
      "line": 3,
      "column": 5,
      "category": "F841",
      "severity": "high",
      "message": "Local variable `unused` is assigned to but never used",
      "analyzer": "ruff",
      "confidence": 0.95
    }
  ]
}
```

---

# Local Development

## Prerequisites

Install the following:

- Python 3.14+
- Node.js
- npm
- Docker
- Git
- PostgreSQL or a hosted PostgreSQL database
- Language-specific analyzer toolchains

For full multi-language analysis, the corresponding compilers/analyzers must be available in the environment.

---

## Clone

```bash
git clone git@github.com:tanmaypsb/BugSlash.git
cd BugSlash
```

---

## Backend

```bash
cd backend

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

Set the database connection:

```bash
export DATABASE_URL="your-postgresql-connection-string"
```

Start FastAPI:

```bash
uvicorn api.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

---

## Frontend

Open another terminal:

```bash
cd frontend

npm install
npm run dev
```

The Vite development server will normally be available at:

```text
http://localhost:5173
```

Configure the backend URL through:

```text
VITE_API_URL
```

Example:

```bash
VITE_API_URL=http://127.0.0.1:8000
```

---

# Docker

The backend includes a containerized analyzer environment containing the required language tooling.

Build:

```bash
cd backend

docker build -t bugslash-backend .
```

Run:

```bash
docker run --rm \
  --env-file .env \
  -p 8000:8000 \
  bugslash-backend
```

The container runs the complete FastAPI service and its analyzer toolchain.

---

# Production Deployment

Current deployment architecture:

```text
                         Internet
                            │
                            ▼
                    ┌───────────────┐
                    │    Vercel     │
                    │ React + Vite  │
                    └───────┬───────┘
                            │
                            │ HTTPS
                            ▼
                    ┌───────────────┐
                    │    Render     │
                    │   FastAPI     │
                    │    Docker     │
                    └───────┬───────┘
                            │
                            │ PostgreSQL
                            ▼
                    ┌───────────────┐
                    │     Neon      │
                    │  PostgreSQL   │
                    └───────────────┘
```

Production services:

- **Frontend:** Vercel
- **Backend:** Render
- **Database:** Neon PostgreSQL

The backend container packages the analyzer dependencies so that analysis behavior is not dependent on the host machine's local development environment.

---

# Database Model

The current persistence layer is intentionally simple.

```text
Project
   │
   └── Scan
         │
         └── Finding
```

Conceptually:

```text
projects
   │
   ├── scans
   │      │
   │      └── findings
   │
   └── ...
```

This provides the foundation for future user accounts, project ownership, scan history, and richer analysis metadata.

---

# Design Principles

### Analyzer Agnostic

The core engine should not depend on one static-analysis ecosystem.

### Normalized Output

Different analyzers should produce a predictable BUGSLASH representation.

### Evidence Before Confidence

A finding's confidence should be tied to available evidence rather than simply trusting an analyzer blindly.

### Separation of Concerns

The system separates:

```text
Detection
   ↓
Normalization
   ↓
Verification
   ↓
Persistence
   ↓
Presentation
```

### Containerized Execution

Language-specific tooling belongs inside a reproducible execution environment rather than relying entirely on the developer's machine.

### Extensibility

Adding a new language should primarily require:

1. Language detection support
2. Analyzer implementation
3. Finding normalization
4. Engine registration
5. Tests

---

# Security Considerations

BUGSLASH analyzes potentially untrusted source code.

The current MVP uses containerization and controlled analyzer execution, but it is **not yet a production-grade arbitrary-code execution sandbox**.

Future hardening includes:

- Stronger container isolation
- Resource limits
- CPU and memory quotas
- Filesystem restrictions
- Network isolation
- Process restrictions
- Safer temporary workspace handling
- Background job isolation

Do not treat the current public MVP as a hardened malicious-code execution environment.

---

# Roadmap

## Phase 1 — Current MVP

- [x] Multi-language detection
- [x] Python analysis
- [x] JavaScript analysis
- [x] TypeScript analysis
- [x] C/C++ analysis
- [x] Java analysis
- [x] Go analysis
- [x] Rust analysis
- [x] Common finding model
- [x] Verification layer
- [x] ZIP project analysis
- [x] PostgreSQL persistence
- [x] Scan history
- [x] React dashboard
- [x] Dockerized backend
- [x] Production backend deployment
- [x] Production frontend deployment

## Phase 2 — Intelligent Fixing

- [ ] Finding-level `Fix This Bug`
- [ ] Fix engine
- [ ] Safe deterministic autofixes
- [ ] Re-run analyzer after modification
- [ ] Fix verification
- [ ] `FIX VERIFIED` state
- [ ] LLM-assisted explanations
- [ ] LLM-assisted complex fixes

Target workflow:

```text
Finding
   ↓
Fix This Bug
   ↓
Fix Engine
   ↓
Safe Fix / LLM Assistance
   ↓
Re-run Analyzer
   ↓
Verification
   ↓
FIX VERIFIED
```

## Phase 3 — Developer Platform

- [ ] Authentication
- [ ] Login / signup
- [ ] User-owned projects
- [ ] Per-user scan history
- [ ] GitHub integration
- [ ] Repository analysis
- [ ] Commit-to-commit regression analysis

## Phase 4 — Scalable Analysis Infrastructure

- [ ] Background job queues
- [ ] Celery
- [ ] Redis
- [ ] WebSocket-based live progress
- [ ] Advanced sandboxing
- [ ] Resource limits
- [ ] Better execution isolation
- [ ] Alembic migrations
- [ ] Expanded database model

## Phase 5 — Larger Architecture

- [ ] Analyzer workers
- [ ] Distributed execution
- [ ] Microservice decomposition where justified
- [ ] Large-scale repository analysis
- [ ] Advanced verification
- [ ] Additional languages and analyzers

---

# What BUGSLASH Is Not

The current MVP is not intended to be:

- A replacement for every static-analysis platform
- A guaranteed proof of program correctness
- A fully autonomous software-engineering agent
- A production-grade sandbox for arbitrary malicious binaries
- A distributed microservice platform

Those capabilities belong to later stages of the roadmap.

---

# Example Detection

Given:

```python
def calculate(x):
    unused = 10
    return x + 1
```

BUGSLASH can surface:

```text
Language     Python
Analyzer     Ruff
Category     F841
Severity     High
Line         2
Column       5
Confidence   0.95

Local variable `unused` is assigned to but never used
```

The same frontend representation can be used for findings originating from different language ecosystems.

---

# Engineering Focus

BUGSLASH is built around a few engineering problems that make the project more than a simple wrapper around static analyzers:

1. **Cross-language abstraction**
2. **Analyzer orchestration**
3. **Finding normalization**
4. **Evidence-based verification**
5. **Reproducible execution environments**
6. **Persistent scan history**
7. **Extensible analyzer architecture**
8. **A path toward verified automated fixing**

The goal is to evolve BUGSLASH from a multi-language analysis dashboard into a developer-oriented code quality and automated remediation platform.

---

# Contributing

Contributions should preserve the separation between:

```text
Analyzer → Normalization → Verification → Persistence → API → UI
```

When adding a new language:

1. Add extension detection.
2. Implement the analyzer adapter.
3. Normalize its diagnostics into `Finding`.
4. Register the analyzer with `BugslashEngine`.
5. Add representative test code.
6. Test the analyzer independently.
7. Test it through the engine.
8. Test the API integration.

---

# License

This project is currently developed as a college software-engineering project.

License information will be added as the project is prepared for broader distribution.
