# Script manual untuk menguji F-06 Resource Recommendation (semantic search).
# Jalankan setelah seed: python scripts/test_resources.py

import logging
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import func, select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models.resource import Resource  # noqa: E402
from app.models.study_plan import StudyPlan  # noqa: E402

logging.basicConfig(level=logging.WARNING)
client = TestClient(app)

results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    results.append((name, condition, detail))
    print(f"[{'PASS' if condition else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


GOAL_PAYLOAD = {
    "topic": "IELTS",
    "current_level": "Beginner",
    "target": "Band 7.0",
    "deadline_months": 3,
    "work_hours_start": "09:00",
    "work_hours_end": "18:00",
    "work_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
    "preferred_study_time": "evening",
    "max_session_minutes": 60,
}


def main() -> None:
    # Katalog ter-seed
    with SessionLocal() as db:
        total = db.scalar(select(func.count()).select_from(Resource))
        with_emb = db.scalar(
            select(func.count()).select_from(Resource).where(Resource.embedding.isnot(None))
        )
    check("katalog punya >= 50 resource", (total or 0) >= 50, f"total={total}")
    check("semua resource punya embedding", total == with_emb, f"emb={with_emb}/{total}")

    # Search (publik)
    r = client.get("/api/resources/search", params={"q": "IELTS listening practice", "top_k": 5})
    check("search -> 200", r.status_code == 200, f"status={r.status_code}")
    items = r.json()
    check("search mengembalikan hasil", len(items) > 0, f"n={len(items)}")
    if items:
        print("  top results:", [(i["name"], i["similarity_score"]) for i in items[:3]])
        check("hasil teratas relevan dengan IELTS", "IELTS" in items[0]["topic"].upper())
        scored = [i["similarity_score"] for i in items]
        check("similarity urut menurun", all(scored[i] >= scored[i + 1] for i in range(len(scored) - 1)))
        check("semua punya similarity_score", all(i["similarity_score"] is not None for i in items))

    # Filter topic + level
    r2 = client.get("/api/resources/search", params={"q": "vocabulary", "topic": "Mandarin", "top_k": 5})
    check("search filter topic -> 200", r2.status_code == 200)
    check("semua hasil bertopic Mandarin", all("Mandarin" in i["topic"] for i in r2.json()))

    # Search tanpa query -> 400
    check("search kosong -> 400", client.get("/api/resources/search").status_code == 400)

    # Recommend untuk plan (auth)
    email = f"res+{uuid.uuid4().hex[:8]}@example.com"
    token = client.post("/api/auth/signup", json={"email": email, "password": "Supersecret123", "name": "Res Tester"}).json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}
    goal = client.post("/api/goals", json=GOAL_PAYLOAD, headers=auth).json()
    # ambil user_id dari /me
    user_id = client.get("/api/auth/me", headers=auth).json()["id"]
    with SessionLocal() as db:
        plan = StudyPlan(
            goal_id=uuid.UUID(goal["id"]),
            user_id=uuid.UUID(user_id),
            plan_data={"goal_summary": "Reach IELTS Band 7 in 3 months focusing on all four skills.", "total_weeks": 12, "milestones": [], "weekly_schedule": [], "resources": []},
            status="active",
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        plan_id = str(plan.id)

    rec = client.get(f"/api/plans/{plan_id}/resources/recommend", headers=auth)
    check("recommend -> 200", rec.status_code == 200, f"status={rec.status_code}")
    rec_items = rec.json()
    check("recommend ada hasil", len(rec_items) > 0, f"n={len(rec_items)}")
    if rec_items:
        print("  recommend top:", [(i["name"], i["similarity_score"]) for i in rec_items[:3]])
    topics = {i["topic"] for i in rec_items}
    check("IELTS goal -> hanya resource IELTS", topics == {"IELTS"}, f"topics={topics}")
    check("tidak ada resource < 0.3", all((i["similarity_score"] or 0) >= 0.3 for i in rec_items))
    check("semua punya relevance_label", all(i["relevance_label"] for i in rec_items))
    labels = {i["relevance_label"] for i in rec_items}
    print("  relevance labels:", labels)

    # min_similarity filter pada search
    r3 = client.get("/api/resources/search", params={"q": "IELTS", "min_similarity": 0.5, "top_k": 10})
    check("search min_similarity=0.5 semua >= 0.5", all((i["similarity_score"] or 0) >= 0.5 for i in r3.json()), f"n={len(r3.json())}")

    check("recommend tanpa token -> 401", client.get(f"/api/plans/{plan_id}/resources/recommend").status_code == 401)

    other = client.post("/api/auth/signup", json={"email": f"o+{uuid.uuid4().hex[:8]}@example.com", "password": "Supersecret123"}).json()["access_token"]
    r_other = client.get(f"/api/plans/{plan_id}/resources/recommend", headers={"Authorization": f"Bearer {other}"})
    check("recommend plan user lain -> 404", r_other.status_code == 404, f"status={r_other.status_code}")

    passed = sum(1 for _, ok, _ in results if ok)
    failed = [name for name, ok, _ in results if not ok]
    print(f"\nSUMMARY: {passed} passed, {len(failed)} failed, {len(results)} total")
    for name in failed:
        print(f"  - FAILED: {name}")


if __name__ == "__main__":
    main()
