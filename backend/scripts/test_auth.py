# Script manual untuk menguji F-09 Authentication.
# Jalankan dari folder backend/: python scripts/test_auth.py

import logging
import sys
import uuid
from pathlib import Path

# Tambahkan root backend ke sys.path agar `app` bisa di-import.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

logging.basicConfig(level=logging.WARNING)

client = TestClient(app)

results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    results.append((name, condition, detail))
    print(f"[{'PASS' if condition else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def main() -> None:
    email = f"auth+{uuid.uuid4().hex[:8]}@example.com"
    password = "Supersecret123"

    # 1. Signup sukses
    r = client.post("/api/auth/signup", json={"email": email, "password": password, "name": "Auth Tester"})
    check("signup sukses -> 201", r.status_code == 201, f"status={r.status_code}")
    body = r.json() if r.status_code == 201 else {}
    token = body.get("access_token")
    check("signup mengembalikan access_token", bool(token))
    check("signup user.email sesuai", body.get("user", {}).get("email") == email)

    # 2. Signup email duplikat -> 409
    r = client.post("/api/auth/signup", json={"email": email, "password": password})
    check("signup email duplikat -> 409", r.status_code == 409, f"status={r.status_code}")

    # 3. Login sukses -> 200
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    check("login sukses -> 200", r.status_code == 200, f"status={r.status_code}")
    login_token = r.json().get("access_token") if r.status_code == 200 else None

    # 4. Login password salah -> 401
    r = client.post("/api/auth/login", json={"email": email, "password": "wrongpassword"})
    check("login password salah -> 401", r.status_code == 401, f"status={r.status_code}")

    # 5. GET /me dengan token valid
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {login_token}"})
    check("GET /me token valid -> 200", r.status_code == 200, f"status={r.status_code}")
    check("GET /me email sesuai", r.json().get("email") == email)

    # 6. GET /me tanpa token -> 401
    r = client.get("/api/auth/me")
    check("GET /me tanpa token -> 401", r.status_code == 401, f"status={r.status_code}")

    # 7. GET /me dengan token invalid -> 401
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.value"})
    check("GET /me token invalid -> 401", r.status_code == 401, f"status={r.status_code}")

    passed = sum(1 for _, ok, _ in results if ok)
    failed = [name for name, ok, _ in results if not ok]
    print(f"\nSUMMARY: {passed} passed, {len(failed)} failed, {len(results)} total")
    for name in failed:
        print(f"  - FAILED: {name}")


if __name__ == "__main__":
    main()
