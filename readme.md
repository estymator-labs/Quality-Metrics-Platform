# QualityMetrics

> Analytical module for the **Sandmark** platform — aggregates AI code review data from MongoDB and exposes management-level quality metrics via a REST API.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Metrics Reference](#metrics-reference)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [API Reference](#api-reference)
- [Data Schema](#data-schema)
- [Seeding Test Data](#seeding-test-data)
- [Dependencies](#dependencies)

---

## Overview

**Sandmark** is an internal tool that fetches diffs from GitLab Merge Requests, sends them to Google Gemini for code review, and stores structured results in MongoDB (`sandmark-history` collection).

**QualityMetrics** builds on top of that data — it turns hundreds of raw review documents into actionable numbers: how many bugs Gemini flagged this month, which files are most problematic, whether test coverage of requirements is improving or declining.

Key properties:

- **Read-only** — QualityMetrics never writes to or modifies any collection.
- **Trend-aware** — every metric is compared against the previous 30-day window and returns a `trend` label (`up` / `down` / `stable`) with a numeric delta.
- **Sample-size guarded** — responses include a `warning` field when fewer than 30 data points are available.

---

## Architecture

```
GitLab MR
    │
    ▼
Sandmark  ──►  sandmark-history (MongoDB)
                      │
          ┌───────────┴────────────┐
          │                        │
          ▼                        ▼
    review_density           defect_escape
    traceability             risk_closure
    soup_completeness
          │
          ▼
    GET /metrics/*  (FastAPI)
```

Each metric is implemented as an independent **agent** — a Python class that connects to MongoDB, runs its aggregation logic, and returns a standardised JSON response.

---

## Metrics Reference

| Agent | Endpoint | What it measures | Source collection |
|---|---|---|---|
| `review_density` | `/metrics/review_density` | Average number of Gemini comments per MR; breakdown by comment type and top problematic files | `sandmark-history` |
| `defect_escape` | `/metrics/defect_escape` | Percentage of MRs with at least one `bug`-type comment; top files with most bugs | `sandmark-history` |
| `traceability` | `/metrics/traceability` | Percentage of requirements covered by at least one test | `requirements` |
| `risk_closure` | `/metrics/risk_closure` | Percentage of closed risks; list of overdue open items | `risks` |
| `soup_completeness` | `/metrics/soup_completeness` | Completeness of the external library (SOUP) register | `soup_register` |

All agents default to the **last 30 days**. If no dated documents exist in that window, the agent falls back to all-time data and sets `"period": "all_time"` in the response.

---

## Project Structure

```
QualityMetrics/
├── main.py                       # FastAPI application entry point
├── .env                          # Local connection config (do not commit)
├── requirements.txt
├── seed_data.py                  # Populates test collections
├── agents/
│   ├── __init__.py               # Agent registry (AGENTS dict)
│   ├── base_agent.py             # MongoDB connection, shared helpers
│   ├── review_density.py
│   ├── defect_escape.py
│   ├── traceability.py
│   ├── risk_closure.py
│   └── soup_completeness.py
├── backend/
│   └── routers/
│       └── metrics.py            # REST endpoints
└── frontend/
    └── dashboard.html            # Static HTML dashboard
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- MongoDB (local instance or MongoDB Atlas)
- A running Sandmark instance with data in `sandmark-history` (or use `seed_data.py` for test data)

### Installation

```bash
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```env
# MongoDB connection string (same database as Sandmark)
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/

# Database name
MONGO_DB_NAME=sandmark-db

# Collection names (defaults shown; override only if needed)
COLLECTION_REVIEW_LOGS=sandmark-history
COLLECTION_REQUIREMENTS=requirements
COLLECTION_RISKS=risks
COLLECTION_SOUP=soup_register
```


### Running the Server

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.  
Interactive Swagger UI: **http://localhost:8000/docs**

---

## API Reference

### Get a single metric

```
GET /metrics/{agent_name}
```

Available agent names: `review_density`, `defect_escape`, `traceability`, `risk_closure`, `soup_completeness`

```bash
curl http://localhost:8000/metrics/review_density
curl http://localhost:8000/metrics/defect_escape
```

### Get all metrics at once

```
GET /metrics/summary
```

```bash
curl http://localhost:8000/metrics/summary
```

Returns a combined `dashboard` object with results from all five agents, plus an `errors` map for any agents that failed.

### Response schema

Every agent returns the same envelope:

```json
{
  "metric": "review_density",
  "value": 3.2,
  "unit": "avg comments per MR",
  "trend": "up",
  "trend_delta": 0.4,
  "period": "last_30_days",
  "sample_size": 87,
  "warning": null,
  "details": { ... }
}
```

| Field | Type | Description |
|---|---|---|
| `metric` | `string` | Agent identifier |
| `value` | `number` | Primary computed value |
| `unit` | `string` | Human-readable unit label |
| `trend` | `"up" \| "down" \| "stable"` | Direction vs. previous 30-day window |
| `trend_delta` | `number` | Absolute difference from previous period |
| `period` | `string` | Time window used for computation |
| `sample_size` | `integer` | Number of documents processed |
| `warning` | `string \| null` | Populated when `sample_size < 30` |
| `details` | `object` | Agent-specific breakdown data |

---

## Data Schema

Agents `review_density` and `defect_escape` require documents in `sandmark-history` with this shape:

```json
{
  "timestamp": "2026-03-28T20:07:15+00:00",
  "mr_url": "https://gitlab.com/org/repo/-/merge_requests/123",
  "review_json": {
    "comments": [
      {
        "file": "src/main.go",
        "line": 42,
        "type": "bug",
        "comment": "Potential nil pointer dereference on line 42."
      }
    ],
    "summary": "Overall review summary from Gemini."
  }
}
```

Valid values for `comment.type`: `bug`, `suggestion`, `style`, `performance`, `security`.

The `timestamp` field accepts both MongoDB `Date` objects and ISO 8601 strings (with or without timezone offset).

---

## Seeding Test Data

If the `requirements`, `risks`, and `soup_register` collections are empty, populate them with sample data:

```bash
python seed_data.py
```

This inserts 20 requirements, 15 risks, and 12 SOUP library entries. The `sandmark-history` collection is intentionally left untouched — it holds real Sandmark review data.

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | ≥ 0.115.0 | Web framework and OpenAPI docs |
| `uvicorn[standard]` | ≥ 0.30.0 | ASGI server |
| `pymongo` | ≥ 4.8.0 | MongoDB driver |
| `python-dotenv` | ≥ 1.0.1 | `.env` file loading |