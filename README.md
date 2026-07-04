# Nash OS Backend Server

FastAPI web API server driving patient surveillance, clinical vital metrics, database logging models, and emergency alert telemetry dispatches.

## Features
- **FastAPI Framework**: High performance REST API endpoints.
- **SQLAlchemy ORM**: Seamless PostgreSQL database mapping.
- **Dynamic Seeding**: Automatically populates database tables with default patients and active triage alerts on initial setup.
- **SQLite Fallback**: Automatically connects to local SQLite file during local development if no Postgres URL is provided.

## Local Development Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/Scripts/activate # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

4. Open swagger docs: `http://localhost:8000/docs`
