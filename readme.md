# QualityMetrics

Moduł analityczny do projektu **Sandmark** — zbiera dane z przeglądów kodu AI i oblicza metryki jakości dla całej organizacji.

---

## Czym jest Sandmark?

**Sandmark** to wewnętrzna aplikacja, która:
1. Pobiera diff z GitLab Merge Request
2. Wysyła go do Google Gemini z promptem do code review
3. Zapisuje strukturyzowany wynik (`review_json`) do MongoDB

Każdy przegląd ląduje w kolekcji `sandmark-history` jako dokument z komentarzami Gemini podzielonymi na typy: `bug`, `suggestion`, `style`, `performance`, `security`.

---

## Po co QualityMetrics?

Sandmark generuje dane — QualityMetrics zamienia je w **metryki zarządcze**.

Zamiast ręcznie przeglądać setki dokumentów w Mongo, wywołujesz jeden endpoint i dostajesz gotowe liczby: ile bugów znajdował Gemini w tym miesiącu, które pliki są najbardziej problematyczne, czy pokrycie wymagań testami rośnie czy spada.

---

## Metryki

| Agent | Co mierzy | Źródło danych |
|---|---|---|
| `review_density` | Średnia liczba komentarzy Gemini na MR | `sandmark-history` |
| `defect_escape` | % MR z co najmniej jednym bug-komentarzem + top problematycznych plików | `sandmark-history` |
| `traceability` | % wymagań pokrytych testami | kolekcja `requirements` |
| `risk_closure` | % zamkniętych ryzyk + przeterminowane pozycje | kolekcja `risks` |
| `soup_completeness` | Kompletność rejestru bibliotek zewnętrznych (SOUP) | kolekcja `soup_register` |

---

## Struktura projektu

```
QualityMetrics/
├── main.py                     # punkt wejścia FastAPI
├── .env                        # konfiguracja połączenia (nie commitować!)
├── requirements.txt
├── agents/
│   ├── __init__.py             # rejestr agentów
│   ├── base_agent.py           # połączenie z MongoDB, metody pomocnicze
│   ├── review_density.py
│   ├── defect_escape.py
│   ├── traceability.py
│   ├── risk_closure.py
│   └── soup_completeness.py
└── backend/
    └── routers/
        └── metrics.py          # endpointy REST
```

---

## Uruchomienie

### 1. Wymagania

- Python 3.11+
- MongoDB (lokalnie lub Atlas)
- Działający Sandmark (żeby były dane w `sandmark-history`)

### 2. Instalacja

```bash
pip install -r requirements.txt
```

### 3. Konfiguracja `.env`

```env
# Połączenie z MongoDB (ta sama baza co Sandmark)
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/

# Nazwa bazy danych
MONGO_DB_NAME=sandmark-db

# Nazwa kolekcji z przeglądami (domyślnie sandmark-history)
COLLECTION_REVIEW_LOGS=sandmark-history
```

### 4. Start

```bash
uvicorn main:app --reload
```

Swagger UI dostępny pod: **http://localhost:8000/docs**

---

## API

### Pojedyncza metryka

```
GET /metrics/{nazwa_agenta}
```

Dostępne nazwy: `review_density`, `defect_escape`, `traceability`, `risk_closure`, `soup_completeness`

```bash
curl http://localhost:8000/metrics/review_density
curl http://localhost:8000/metrics/defect_escape
```

### Dashboard — wszystkie metryki naraz

```bash
curl http://localhost:8000/metrics/summary
```

### Format odpowiedzi

Każdy agent zwraca ten sam schemat:

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

Pole `warning` jest wypełnione gdy `sample_size < 30` — wyniki mogą być wtedy mało miarodajne.

---

## Dane testowe

Jeśli bazy `requirements`, `risks` i `soup_register` są puste, możesz wypełnić je przykładowymi danymi:

```bash
python seed_data.py
```

Skrypt wstawia 20 wymagań, 15 ryzyk i 12 bibliotek. Kolekcji `sandmark-history` nie rusza — tam są Twoje realne dane z Sandmarka.

---

## Zależności między projektami

```
GitLab MR
    │
    ▼
Sandmark  ──►  sandmark-history (MongoDB)
                      │
                      ▼
              QualityMetrics  ──►  GET /metrics/*
```

QualityMetrics jest **tylko do odczytu** — nie modyfikuje żadnej kolekcji.

---

## Wymagania dotyczące kolekcji sandmark-history

Agent `review_density` i `defect_escape` oczekują dokumentów w tej strukturze:

```json
{
  "timestamp": "2026-03-28T20:07:15+00:00",
  "mr_url": "https://gitlab.com/org/repo/-/merge_requests/123",
  "review_json": {
    "comments": [
      { "file": "src/main.go", "line": 42, "type": "bug", "comment": "..." }
    ],
    "summary": "..."
  }
}
```

Pole `type` w komentarzach może przyjmować wartości: `bug`, `suggestion`, `style`, `performance`, `security`.