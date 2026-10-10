# Script manual untuk menguji LLM service (basic, JSON mode, streaming).
# Jalankan dari folder backend/: python scripts/test_llm.py

import asyncio
import logging
import sys
from pathlib import Path

# Tambahkan root backend ke sys.path agar `app` bisa di-import.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import BaseModel  # noqa: E402

from app.services.llm import (  # noqa: E402
    chat_completion,
    chat_completion_json,
    chat_completion_stream,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

SYSTEM = "You are Study Agent. Jawab singkat dalam Bahasa Indonesia."


class FeasibilityCheck(BaseModel):
    # Contoh schema untuk menguji JSON mode + validasi.
    verdict: str
    confidence: float
    reasoning: str


async def test_basic() -> None:
    print("\n=== 1. Basic completion ===")
    result = await chat_completion(
        "Sebutkan 1 tips belajar efektif untuk pekerja full-time.",
        system=SYSTEM,
        temperature=0.7,
        max_tokens=200,
        thinking=False,
    )
    print("content:", result.content.strip())
    print("model:", result.model)
    print("latency_ms:", result.latency_ms)
    print("usage:", result.usage.model_dump())


async def test_json() -> None:
    print("\n=== 2. JSON mode ===")
    prompt = (
        "Nilai apakah target berikut realistis: belajar Mandarin dari nol ke HSK 4 "
        "dalam 6 bulan, tersedia 10 jam/minggu. Balas JSON dengan field: "
        "verdict (string), confidence (0-1), reasoning (string)."
    )
    result = await chat_completion_json(
        prompt,
        system=SYSTEM,
        schema=FeasibilityCheck,
        temperature=0.3,
        max_tokens=400,
        thinking=False,
    )
    print("content:", result.content.strip())
    print("parsed:", result.data)
    print("latency_ms:", result.latency_ms)
    print("usage:", result.usage.model_dump())


async def test_stream() -> None:
    print("\n=== 3. Streaming ===")
    stream = chat_completion_stream(
        "Buat 1 kalimat semangat belajar dalam Bahasa Indonesia.",
        system=SYSTEM,
        temperature=0.7,
        max_tokens=200,
        thinking=False,
    )
    print("content: ", end="", flush=True)
    async for chunk in stream:
        print(chunk, end="", flush=True)
    print()


async def main() -> None:
    await test_basic()
    await test_json()
    await test_stream()
    print("\nSelesai. Semua test selesai tanpa exception.")


if __name__ == "__main__":
    asyncio.run(main())
