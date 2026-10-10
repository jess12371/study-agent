# Database — Study Agent

Folder untuk migration dan skema database (PostgreSQL 16 + pgvector).

> Status: placeholder. Alembic akan diinisialisasi di sini pada tahap setup berikutnya.

Rencana tabel awal (PRD section 11 `Data Model`):

- `users`
- `goals`
- `study_plans` (kolom `plan_data` bertipe JSONB)
- `progress_entries`
- `resources`

Isi folder:

- `migrations/` — file migration Alembic
