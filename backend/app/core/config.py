# Konfigurasi aplikasi — load environment variable dari backend/.env via Pydantic Settings.

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Root folder backend (…/backend). Dipakai untuk resolve lokasi .env.
BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # Model konfigurasi: baca .env, abaikan env var yang tidak dikenal.
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App ---
    app_env: str = "development"
    cors_origins: str = "http://localhost:3000"

    # --- LLM: DeepSeek V4.1 Flash ---
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-flash"
    # Batas token output untuk F-02 feasibility check (topik kompleks butuh lebih banyak).
    feasibility_max_tokens: int = 16384

    # --- Performance tuning (F-03 plan generation / F-05 reschedule apply) ---
    # Detail mingguan dibatasi agar output lebih pendek (minggu lain ikut tema milestone).
    plan_detailed_weeks: int = 2
    plan_max_tokens: int = 16384
    # Plan generation berbasis pola → reasoning "medium" cukup dan jauh lebih cepat.
    plan_reasoning_effort: str = "medium"
    reschedule_apply_reasoning_effort: str = "medium"

    # --- Database: PostgreSQL (Supabase) + pgvector ---
    database_url: str

    # --- Auth / JWT (F-09) ---
    jwt_secret: str = "change-me-to-a-long-random-string-at-least-32-chars"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080

    @property
    def cors_origin_list(self) -> list[str]:
        # Pisahkan daftar origin dengan koma → list.
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


# Singleton settings — import `settings` ini di seluruh aplikasi.
settings = Settings()
