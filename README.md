# Seora | Premium Music CRM

![Status](https://img.shields.io/badge/status-active-brightgreen)
![Stack](https://img.shields.io/badge/stack-Flask%20%2B%20MongoDB-blue)
![Python](https://img.shields.io/badge/python-3.12-informational)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

A full-featured CRM for musical instrument shops and luthier workshops, built with Python, Flask, and MongoDB. Runs instantly — no database setup required.

---

## For the Technical Recruiter

> This project demonstrates:
> - **Storage Interface Adapter Pattern** — dual-backend architecture (MongoDB / JSON) with zero code changes at the route level. The app detects MongoDB availability at startup and falls back gracefully to a JSON sandbox.
> - **REST API design** — versioned API (`/api/v1/*`) with an interactive explorer UI.
> - **Production-ready setup** — Gunicorn + Docker + docker-compose with environment-based secrets management.
> - **Clean separation of concerns** — storage logic isolated in `storage.py`, route logic in `app.py`, templates in Jinja2.

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Backend | Python + Flask | 3.12 / 3.0.3 |
| Database | MongoDB (primary) | 7.0 |
| DB Fallback | JSON file (built-in) | — |
| Driver | PyMongo | 4.11.1 |
| Production server | Gunicorn | 23.0.0 |
| Containerization | Docker + Compose | — |
| Frontend | Jinja2 + Vanilla CSS | — |

---

## Quick Start — No Setup Required

You do **not** need MongoDB or Docker to run this project.

```bash
# 1. Clone and install
git clone https://github.com/Michael-Lascano/seora-crm-mongodb.git
cd seora-crm-mongodb
pip install -r requirements.txt

# 2. Run
python app.py
```

Open **http://127.0.0.1:3000**

The system automatically detects that MongoDB is unavailable and activates **JSON Sandbox Mode**, loading 15 customers, 25 instruments, 20 transactions, and 10 repair orders — ready to explore.

---

## Production Setup (with MongoDB)

### Option A — Docker (recommended)

```bash
# Copy and edit environment variables
cp .env.example .env

# Start CRM + MongoDB together
docker-compose up -d
```

### Option B — Local MongoDB

```bash
# Set up environment
cp .env.example .env
# Edit .env: set MONGO_URI and SECRET_KEY

# Create virtual environment and install
python -m venv venv
venv\Scripts\activate     # Windows
# source venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
python app.py
```

Access at **http://127.0.0.1:3000**

---

## REST API v1

| Endpoint | Description |
|---|---|
| `GET /api/v1/instruments` | Full inventory list |
| `GET /api/v1/customers` | Customer directory |
| `GET /api/v1/transactions` | Transaction log (sorted by date) |
| `GET /api/v1/repairs` | Workshop repair orders |
| `GET /api/v1/dashboard` | Financial summary + storage mode |
| `GET /api` | Interactive API Explorer |

---

## Project Structure

```
seora-crm-mongodb/
├── app.py               # Flask routes, business logic, seed data
├── storage.py           # Storage Adapter (MongoDB / JSON dual-backend)
├── requirements.txt     # Python dependencies
├── Dockerfile           # Production container (python:3.12-slim)
├── docker-compose.yml   # CRM + MongoDB stack
├── .env.example         # Environment variable template
├── test_crm.py          # Automated QA suite (25 HTTP checks)
├── templates/
│   ├── base.html        # Layout base
│   ├── dashboard.html   # KPI dashboard
│   ├── instruments.html # Inventory management
│   ├── repairs.html     # Workshop Kanban
│   ├── transactions.html
│   ├── customers.html
│   └── partials/        # Reusable modal components
└── static/css/
    └── styles.css       # Custom dark design system
```

---

## Running the QA Suite

With the server running locally:

```bash
python test_crm.py
```

Runs 25 automated checks across all page routes, REST endpoints, and data integrity assertions.

---

## Environment Variables

Copy `.env.example` to `.env` and configure:

```env
SECRET_KEY=your-secret-key-here
MONGO_URI=mongodb://127.0.0.1:27017/crm
PORT=3000
```

> ⚠️ Never commit `.env` to version control. It is excluded by `.gitignore`.
