# Finanzas Backend

Personal finance ETL + API backend for processing bank statements and managing transactions.

## Tech Stack

- Python 3.12+
- FastAPI
- SQLAlchemy 2.0
- Alembic (migrations)
- PostgreSQL
- Pydantic v2
- pandas + openpyxl (XLSX parsing)
- pdfplumber (PDF parsing)
- httpx (LLM HTTP client)

## Features

- File upload endpoint for bank statements (XLSX and PDF)
- ETL pipeline for Bancolombia XLSX and RappiCard/Davivienda PDF statements
- Automatic transaction categorization (rules-first + LLM fallback via OpenRouter)
- Manual recategorization endpoint (seeds new examples to improve future LLM calls)
- Canonical transaction storage with deduplication
- Full traceability from transactions to source files and raw rows
- REST API for querying and managing transactions

## Setup

### 1. Install dependencies

Using pip:
```bash
pip install -e .
```

Or using uv (recommended):
```bash
uv pip install -e .
```

### 2. Start PostgreSQL

```bash
docker-compose up -d
```

This starts a PostgreSQL instance on `localhost:5433` with:
- Database: `finanzas_db`
- User: `finanzas`
- Password: `finanzas123`

### 3. Configure environment

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Edit `.env` if needed (defaults should work with docker-compose).

For LLM categorization, add your OpenRouter API key:
```
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=openai/gpt-4o-mini   # or any model on OpenRouter
LLM_CONFIDENCE_THRESHOLD=0.70
```

If `OPENROUTER_API_KEY` is empty, the pipeline skips LLM and falls back to `OTROS` for unmatched transactions.

### 4. Run migrations

```bash
alembic upgrade head
```

### 5. Create a test account

Before uploading files, create an account in the database:

```bash
python -c "
from app.db.session import SessionLocal
from app.models import Account

db = SessionLocal()
account = Account(
    bank_name='Bancolombia',
    account_name='Cuenta de Ahorros',
    currency='COP'
)
db.add(account)
db.commit()
db.refresh(account)
print(f'Created account with ID: {account.id}')
"
```

Save the account ID for use in API requests.

### 6. Seed category examples

```bash
python scripts/seed_categories.py
```

This inserts ~55 manually curated examples into `category_examples` used as few-shot context for LLM categorization. Safe to run multiple times (idempotent).

## Run API

```bash
uvicorn app.main:app --reload
```

API will be available at `http://localhost:8000`.

Interactive docs: `http://localhost:8000/docs`

## API Usage

### 1. Upload a file

Bancolombia XLSX:
```bash
curl -X POST http://localhost:8000/files/upload \
  -F "file=@/path/to/bancolombia_statement.xlsx" \
  -F "bank_name=Bancolombia" \
  -F "account_id=YOUR_ACCOUNT_UUID"
```

RappiCard/Davivienda PDF:
```bash
curl -X POST http://localhost:8000/files/upload \
  -F "file=@/path/to/rappicard_statement.pdf" \
  -F "bank_name=rappicard" \
  -F "account_id=YOUR_ACCOUNT_UUID"
```

Response:
```json
{
  "file_id": "...",
  "parse_status": "UPLOADED",
  "file_hash": "...",
  "original_filename": "bancolombia_statement.xlsx",
  "uploaded_at": "2026-03-05T..."
}
```

### 2. Process ETL

```bash
curl -X POST "http://localhost:8000/etl/process/FILE_UUID?account_id=ACCOUNT_UUID"
```

Response:
```json
{
  "parsed_rows": 150,
  "inserted_transactions": 145,
  "duplicates_skipped": 5,
  "status": "PROCESSED"
}
```

### 3. Reset a bad ETL run

```bash
curl -X DELETE "http://localhost:8000/etl/reset/FILE_UUID"
```

Deletes all transactions and raw rows for that file and resets its status to `UPLOADED` so it can be reprocessed.

### 4. List transactions

Get all transactions for an account:
```bash
curl "http://localhost:8000/transactions?account_id=ACCOUNT_UUID"
```

Filter by specific months:
```bash
curl "http://localhost:8000/transactions?account_id=ACCOUNT_UUID&months=2024-01,2024-02"
```

Response:
```json
[
  {
    "id": "...",
    "account_id": "...",
    "source_file_id": "...",
    "posted_at": "2024-01-15",
    "description_raw": "Compra en TIENDA XYZ",
    "description_clean": "COMPRA EN TIENDA XYZ",
    "amount": "-50000.00",
    "currency": "COP",
    "merchant_guess": null,
    "details_json": {
      "auth_number": "123456",
      "cuotas": "1",
      ...
    },
    "category": "TRANSPORTE",
    "category_confidence": "0.95",
    "category_method": "RULES",
    "merchant_guess": "Dlo*Didi",
    "created_at": "2026-03-05T..."
  }
]
```

### 5. Manually recategorize a transaction

```bash
curl -X PATCH "http://localhost:8000/transactions/TX_UUID/categorize" \
  -H "Content-Type: application/json" \
  -d '{"category": "OCIO", "description_clean": "NETFLIX DL"}'
```

Sets `category_method=USER`, `category_confidence=1.0`, and optionally seeds a new example into `category_examples`.

## Categorization Flow

```
Parsed transaction
       │
       ▼
  Rules-first (keyword matching)
       │
  match? ──yes──► category_method=RULES, confidence=0.95
       │
      no
       ▼
  OpenRouter LLM (few-shot with category_examples)
       │
  confidence ≥ 0.70? ──yes──► category_method=LLM
       │
      no
       ▼
  OTROS, confidence=0.0
```

### Categories

| Category | Description |
|---|---|
| HOGAR | Supermercados, servicios del hogar, telefonía |
| DOMICILIOS | Rappi, Didi Food |
| CARRO | Gasolina, mantenimiento |
| TRANSPORTE | Uber, Didi, parqueaderos |
| OCIO | Streaming, bares, viajes, entretenimiento |
| RESTAURANTES | Restaurantes y cafés |
| ROPA | Ropa y accesorios |
| SALUD | Droguerías, IPS, medicamentos |
| PRESTACIONES | Seguros, servicios financieros |
| REGALOS | Regalos y donaciones |
| EDUCACION | Cursos, suscripciones educativas |
| TRABAJO | Herramientas de trabajo (OpenAI, Cursor, Claude) |
| COBRO_BANCARIO | Cuotas de manejo |
| PAGO | Abonos y pagos a la tarjeta |
| OTROS | Sin categoría definida |

## Database Schema

### accounts
- Stores bank account information
- Each transaction belongs to one account

### source_files
- Stores uploaded file metadata
- Tracks processing status (UPLOADED/PROCESSED/FAILED)
- Deduplicates files by hash

### raw_rows
- Stores raw parsed data from files
- Maintains full traceability to source

### transactions
- Canonical transaction format
- Deduplicated by fingerprint (source_file_id + row_index)
- Amount convention: expenses are NEGATIVE, income is POSITIVE
- Stores `category`, `category_confidence`, `category_method`, `merchant_guess`

### category_examples
- Curated examples used as few-shot context for LLM categorization
- Seeded via `scripts/seed_categories.py`
- Grows automatically when users manually recategorize transactions

## Parsers

### Bancolombia XLSX (`bank_name=Bancolombia`, `.xlsx`)

Handles Bancolombia credit card statements (PESOS and DOLARES sheets):
- Multiple transaction blocks per sheet
- Transaction rows with 9 columns
- Continuation rows for additional details
- Colombian number format (thousands: `.`, decimals: `,`)
- Automatic sign conversion to canonical format

### RappiCard / Davivienda PDF (`bank_name=rappicard`, `.pdf`)

Handles RappiCard/Davivienda credit card PDF statements:
- Extracts text with `pdfplumber`
- Finds the "Detalle de transacciones" section
- Line-based parsing with multi-line description accumulation
- Two row formats: purchases (with installment/capital detail) and payments (`N/A` fields)
- Colombian number format (thousands: `.`, decimals: `,`)

Standalone parser test (run from project root):
```bash
python scripts/test_rappicard_parser.py data/uploads/rappi-0226.pdf
```

## Development

### Run migrations

Create new migration:
```bash
alembic revision --autogenerate -m "description"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback:
```bash
alembic downgrade -1
```

### Project Structure

```
/app
  main.py              # FastAPI application
  /api
    router.py          # API router setup
    deps.py            # Dependencies (DB session)
    /routes
      files.py         # File upload endpoint
      etl.py           # ETL processing endpoint
      transactions.py  # Transaction listing endpoint
  /core
    config.py          # Settings and configuration
  /db
    session.py         # Database session management
    base.py            # SQLAlchemy Base
  /models
    enums.py           # Category and CategoryMethod enums
    account.py
    source_file.py
    raw_row.py
    transaction.py
    category_example.py
  /schemas
    file.py            # Pydantic schemas for files
    transaction.py     # Pydantic schemas for transactions
    etl.py             # Pydantic schemas for ETL
  /services
    storage.py         # File storage service
    llm_client.py      # OpenRouter HTTP client
  /etl
    pipeline.py        # Main ETL pipeline orchestration
    normalization.py   # Transaction normalization
    dedupe.py          # Deduplication logic
    categorization.py  # Rules-first + LLM-fallback categorization
    /parsers
      bancolombia_xlsx_pesos.py      # Bancolombia XLSX parser
      rappicard_davivienda_pdf.py    # RappiCard/Davivienda PDF parser
  /utils
    text.py            # Text normalization utilities
    hashing.py         # Hashing utilities
/scripts
  seed_categories.py        # Seed curated category examples
  test_rappicard_parser.py  # Standalone PDF parser smoke test
```

## License

Proprietary
