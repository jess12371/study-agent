# Seed katalog resource berkualitas ke database (idempoten).
# Jalankan dari folder backend/: python scripts/seed_resources.py

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.resource_service import seed_resources  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def main() -> None:
    added = seed_resources()
    print(f"Seed selesai. {added} resource baru ditambahkan.")


if __name__ == "__main__":
    main()
