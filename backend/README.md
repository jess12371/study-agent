# Backend — Study Agent

Backend API Study Agent berbasis **FastAPI** (Python 3.11+). Saat ini masih **skeleton**: hanya ada endpoint health check, belum ada fitur.

## Struktur

```
backend/
├── app/
│   ├── __init__.py
│   └── main.py          # entry point FastAPI + endpoint /api/health
├── .env.example         # template environment
├── requirements.txt     # dependencies
└── README.md
```

## Prasyarat

- Python 3.11 atau lebih baru
- PostgreSQL 16 (untuk nanti, belum dibutuhkan untuk menjalankan skeleton)

## Cara Run

Dari folder `backend/`:

```bash
# 1. Bikin virtual environment
python -m venv .venv

# 2. Aktifkan (Windows PowerShell)
.venv\Scripts\Activate.ps1
#    macOS / Linux:
# source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Siapkan environment
copy .env.example .env   # Windows
# cp .env.example .env   # macOS / Linux

# 5. Jalankan server (mode development, auto-reload)
uvicorn app.main:app --reload --port 8000
```

Server jalan di `http://localhost:8000`.

## Test Endpoint Health

```bash
curl http://localhost:8000/api/health
```

Respons yang diharapkan:

```json
{"status": "ok", "service": "study-agent-api"}
```

Dokumentasi API otomatis tersedia di:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Database (Alembic)

Migrasi dikelola dengan Alembic, konfigurasi ada di `alembic.ini` dan `migrations/`.
URL database dibaca otomatis dari `DATABASE_URL` di `.env`.

```bash
# Terapkan semua migration
alembic upgrade head

# Bikin migration baru dari perubahan model
alembic revision --autogenerate -m "deskripsi perubahan"

# Rollback satu langkah
alembic downgrade -1
```

Verifikasi tabel via `psql`:

```bash
psql "$DATABASE_URL" -c "\dt public.*"
```

## LLM Service (DeepSeek)

Wrapper async DeepSeek v4.1 Flash ada di `app/services/llm.py`, dengan 3 mode:
`chat_completion`, `chat_completion_json`, dan `chat_completion_stream`.
API key dibaca dari `.env` (tidak pernah di-hardcode).

```bash
# Uji koneksi + 3 mode sekaligus
python scripts/test_llm.py
```

## Catatan

- Endpoint aplikasi nanti memakai prefix `/api` (lihat PRD section 12 `API Endpoints`).
- Konfigurasi LLM (DeepSeek) belum diimplementasi; hanya variabel `.env` yang disiapkan.
