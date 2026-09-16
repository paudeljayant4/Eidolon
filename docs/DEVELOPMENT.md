# Eidolon Development Guide

## Prerequisites
- Docker and Docker Compose
- Node.js 20+
- Python 3.12+
- uv or pip

## Local Development

### Using Docker Compose
```bash
docker compose up --build
```
This starts:
- **db**: PostgreSQL on port 5432
- **redis**: Redis on port 6379
- **backend**: FastAPI on port 8000
- **frontend**: Next.js on port 3000

### Without Docker

#### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Package Structure

```
eidolon/
├── package.json              - Root workspace config
├── frontend/               - Next.js + TypeScript + Tailwind + R3F
├── backend/              - FastAPI + Python
├── simulation/           - Core deterministic engine
├── agents/               - Cognition layer
├── shared/               - Shared types/schemas
├── docs/                 - Documentation
├── docker/               - Docker configs
└── .github/              - CI/CD
```

## Available Scripts

### Root (package.json)
- `npm run lint` - Basic lint placeholder
- `npm run typecheck` - Basic typecheck placeholder
- `npm run test` - Basic test placeholder

### Frontend (frontend/package.json)
- `npm run dev` - Start Next.js dev server
- `npm run build` - Build Next.js
- `npm run lint` - Run ESLint
- `npm run test` - Run Vitest

### Backend (backend/package.json)
- `npm run dev` - Start FastAPI with uvicorn
- `npm run lint` - Run ruff
- `npm run typecheck` - Run mypy
- `npm run test` - Run pytest

### Simulation (simulation/package.json)
- `npm run build` - Build TypeScript
- `npm run test` - Run Vitest

### Agents (agents/package.json)
- `npm run build` - Build TypeScript
- `npm run test` - Run Vitest

### Shared (shared/package.json)
- `npm run build` - Build TypeScript
- `npm run test` - Run Vitest