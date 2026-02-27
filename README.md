# 🚀 Future You
### AI-Powered Career Intelligence Platform

Future You is a full-stack AI-powered career intelligence system designed to provide semantic job recommendations, resume intelligence, and skill gap analysis using modern AI and multi-database architecture.

This project combines secure authentication, vector embeddings, graph-based reasoning, and hybrid ranking to deliver explainable and personalized career insights.

---

## 🌱 Features

- 🔐 Hybrid Authentication (Firebase + JWT)
- 📄 Resume Upload & AI-Based Skill Extraction
- 🧠 Semantic Job Matching (Vector Similarity Search)
- 🔍 Hybrid Ranking (Vector + Keyword Search)
- 🧩 Skill Gap Detection
- 🛣️ Learning Path Generation (Neo4j Graph)
- ⚡ Multi-Database Integration
- 🐳 Docker-based Development Setup

---

## 🏗️ System Architecture

### 🔹 Frontend
- Next.js (App Router)
- TypeScript
- Tailwind CSS
- Firebase Authentication
- Protected Routes
- Theme System (Light/Dark/System)

### 🔹 Backend
- Flask (Application Factory Pattern)
- SQLAlchemy (PostgreSQL)
- Flask-Migrate
- Flask-Limiter
- Structlog Logging
- JWT Authentication

### 🔹 AI & Data Infrastructure
- 🤖 HuggingFace Sentence Transformers (`all-MiniLM-L6-v2`)
- 📦 Qdrant (Vector Database)
- 🧠 Neo4j (Graph Database)
- 🔍 Elasticsearch (Keyword Search)
- ⚡ Redis (Caching & Rate Limiting)

---

## 🔐 Authentication Flow

1. User logs in via Firebase (frontend)
2. Firebase ID token sent to backend
3. Backend verifies token using Firebase Admin SDK
4. Backend issues JWT access & refresh tokens
5. Protected APIs validate JWT

> This ensures secure session ownership on the backend.

---

## 🤖 AI Recommendation Engine

### Resume Intelligence
- PDF Parsing
- Skill Extraction & Normalization
- Embedding Generation
- Storage in Qdrant

### Job Recommendation
- User profile vector generation
- Vector similarity search (Qdrant)
- Keyword search (Elasticsearch)
- Hybrid ranking (60% vector + 40% keyword)
- Explainable match score

### Skill Gap Analysis
- Compare user skills vs job requirements
- Match percentage calculation
- Missing skill detection
- Learning path generation (Neo4j)

---

## 📂 Project Structure

```
backend/
├── app/
│   ├── agents/
│   ├── models/
│   ├── routes/
│   ├── services/
│   └── utils/
frontend/
job_matcher_system/
docker-compose.yml
```

---

## 🐳 Running with Docker

```bash
docker-compose up --build
```

**Services spun up:**
- Backend (Flask)
- PostgreSQL
- Qdrant
- Neo4j
- Elasticsearch
- Redis

---

## 💻 Running Locally (Without Docker)

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## 🔥 Engineering Challenges Solved

- Next.js hydration mismatch debugging
- React Strict Mode double render handling
- Infinite authentication redirect loop fixes
- Qdrant SDK migration (`search()` → `query_points()`)
- Multi-service initialization handling
- Hybrid authentication architecture design

---

## 📊 Current Status

| Feature | Status |
|---|---|
| Authentication | ✅ Stable |
| Resume Processing | ✅ Working |
| Vector Search (Qdrant v1.16+) | ✅ Operational |
| Hybrid Recommendation Engine | ✅ Active |
| Elasticsearch | ✅ Integrated |
| Neo4j Skill Graph | ✅ Connected |

---

## 🚀 Roadmap

- [ ] Job Scraping Agent Integration
- [ ] Background Task Queue (Celery + Redis)
- [ ] Resume → Auto Profile Vector Pipeline
- [ ] Skill Visualization Dashboard
- [ ] Production Deployment (Gunicorn + Docker)
- [ ] Multi-Agent Career Assistant System

---

## 🧠 Technical Summary

Future You is a full-stack AI-powered career platform built with **Next.js** and **Flask**, using **Firebase authentication**, **JWT security**, **vector embeddings**, and **multi-database architecture** to deliver intelligent and explainable job recommendations.

---
⭐ If you find this project interesting, feel free to star the repository!
