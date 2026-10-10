# Service F-06 — Resource Recommendation (semantic search dengan pgvector).
# Menyimpan katalog resource berkualitas + embedding (all-MiniLM-L6-v2, 384 dim).

import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.goal import Goal
from app.models.resource import Resource
from app.models.study_plan import StudyPlan
from app.schemas.resource import ResourceCreate, ResourceResponse
from app.services.embedding_service import generate_embedding, generate_embeddings

logger = logging.getLogger(__name__)

# Boost skor untuk topic yang cocok; penalti kalau topik berbeda.
TOPIC_BOOST = 0.1
TOPIC_MISMATCH_PENALTY = 0.2

# Katalog resource berkualitas (sumber nyata, mayoritas gratis).
RESOURCE_SEED: list[dict] = [
    # --- IELTS ---
    {"topic": "IELTS", "type": "website", "name": "IELTS Liz", "url": "https://ieltsliz.com/", "level": "beginner", "is_free": True, "description": "Free IELTS lessons, tips, and model answers for all four skills.", "skills": ["listening", "reading", "writing", "speaking"]},
    {"topic": "IELTS", "type": "website", "name": "British Council — Take IELTS", "url": "https://takeielts.britishcouncil.org/take-ielts/prepare", "level": "beginner", "is_free": True, "description": "Official British Council IELTS preparation materials and free practice tests.", "skills": ["listening", "reading", "writing", "speaking"]},
    {"topic": "IELTS", "type": "website", "name": "IELTS Online Tests", "url": "https://ieltsonlinetests.com/", "level": "intermediate", "is_free": True, "description": "Free IELTS practice tests with instant scoring and explanations.", "skills": ["reading", "listening"]},
    {"topic": "IELTS", "type": "video", "name": "E2 IELTS (YouTube)", "url": "https://www.youtube.com/@E2IELTS", "level": "intermediate", "is_free": True, "description": "Strategy videos and live classes for IELTS writing and speaking.", "skills": ["writing", "speaking"]},
    {"topic": "IELTS", "type": "app", "name": "IELTS Vocabulary (Anki decks)", "url": "https://ankiweb.net/shared/decks?search=ielts", "level": "intermediate", "is_free": True, "description": "Spaced-repetition decks for high-frequency IELTS vocabulary.", "skills": ["vocabulary", "reading"]},
    # --- TOEFL ---
    {"topic": "TOEFL", "type": "website", "name": "ETS TOEFL iBT", "url": "https://www.ets.org/toefl.html", "level": "intermediate", "is_free": True, "description": "Official TOEFL information, sample questions, and test prep resources.", "skills": ["reading", "listening", "writing", "speaking"]},
    {"topic": "TOEFL", "type": "website", "name": "TOEFL Resources", "url": "https://www.toeflresources.com/", "level": "intermediate", "is_free": True, "description": "Free guides, templates, and practice questions for TOEFL.", "skills": ["writing", "speaking"]},
    {"topic": "TOEFL", "type": "website", "name": "Magoosh TOEFL Blog", "url": "https://magoosh.com/toefl/", "level": "intermediate", "is_free": True, "description": "Study tips, vocabulary, and practice questions from Magoosh.", "skills": ["vocabulary", "reading"]},
    # --- Python ---
    {"topic": "Python", "type": "website", "name": "Python for Everybody (PY4E)", "url": "https://www.py4e.com/", "level": "beginner", "is_free": True, "description": "Beginner Python course covering variables, loops, functions, and files.", "skills": ["programming", "problem solving"]},
    {"topic": "Python", "type": "book", "name": "Automate the Boring Stuff with Python", "url": "https://automatetheboringstuff.com/", "level": "beginner", "is_free": True, "description": "Free online book teaching practical Python scripting and automation.", "skills": ["programming", "automation"]},
    {"topic": "Python", "type": "website", "name": "Real Python Tutorials", "url": "https://realpython.com/", "level": "intermediate", "is_free": True, "description": "In-depth Python tutorials from basics to advanced topics.", "skills": ["programming", "web development"]},
    {"topic": "Python", "type": "video", "name": "freeCodeCamp — Python for Beginners", "url": "https://www.youtube.com/watch?v=rfscVS0vtbw", "level": "beginner", "is_free": True, "description": "Full-length beginner Python video course with hands-on examples.", "skills": ["programming"]},
    {"topic": "Python", "type": "website", "name": "W3Schools Python Tutorial", "url": "https://www.w3schools.com/python/", "level": "beginner", "is_free": True, "description": "Quick reference and interactive exercises for Python basics.", "skills": ["programming"]},
    {"topic": "Python", "type": "website", "name": "Kaggle Learn — Python", "url": "https://www.kaggle.com/learn/python", "level": "beginner", "is_free": True, "description": "Hands-on Python micro-course with in-browser coding exercises.", "skills": ["programming", "data analysis"]},
    {"topic": "Python", "type": "tool", "name": "Replit", "url": "https://replit.com/", "level": "beginner", "is_free": True, "description": "Browser IDE to write and run Python without local setup.", "skills": ["programming"]},
    # --- JavaScript ---
    {"topic": "JavaScript", "type": "website", "name": "MDN Web Docs — JavaScript", "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript", "level": "beginner", "is_free": True, "description": "Authoritative reference and guides for JavaScript and the web platform.", "skills": ["programming", "web development"]},
    {"topic": "JavaScript", "type": "website", "name": "javascript.info", "url": "https://javascript.info/", "level": "beginner", "is_free": True, "description": "Modern, comprehensive JavaScript tutorial from fundamentals to advanced.", "skills": ["programming", "web development"]},
    {"topic": "JavaScript", "type": "book", "name": "Eloquent JavaScript", "url": "https://eloquentjavascript.net/", "level": "intermediate", "is_free": True, "description": "Free online book covering JS fundamentals, browser, and Node.js.", "skills": ["programming", "web development"]},
    {"topic": "JavaScript", "type": "website", "name": "freeCodeCamp JavaScript Algorithms", "url": "https://www.freecodecamp.org/learn/javascript-algorithms-and-data-structures/", "level": "beginner", "is_free": True, "description": "Interactive certification course on JS algorithms and data structures.", "skills": ["programming", "algorithms"]},
    # --- Mandarin ---
    {"topic": "Mandarin", "type": "app", "name": "HelloChinese", "url": "https://www.hellochinese.cc/", "level": "beginner", "is_free": True, "description": "Beginner Mandarin app with pinyin, tones, and HSK-aligned lessons.", "skills": ["listening", "speaking", "vocabulary"]},
    {"topic": "Mandarin", "type": "website", "name": "HSK Academy", "url": "https://www.hskacademy.com/", "level": "beginner", "is_free": True, "description": "Free HSK vocabulary lists and grammar explanations by level.", "skills": ["vocabulary", "reading"]},
    {"topic": "Mandarin", "type": "video", "name": "Mandarin Corner (YouTube)", "url": "https://www.youtube.com/@MandarinCorner2", "level": "intermediate", "is_free": True, "description": "Listening practice with real conversations and HSK-based lessons.", "skills": ["listening", "speaking"]},
    {"topic": "Mandarin", "type": "app", "name": "Pleco", "url": "https://www.pleco.com/", "level": "beginner", "is_free": True, "description": "Popular Chinese dictionary and flashcard app.", "skills": ["vocabulary", "reading"]},
    {"topic": "Mandarin", "type": "app", "name": "Anki + HSK decks", "url": "https://ankiweb.net/shared/decks?search=hsk", "level": "beginner", "is_free": True, "description": "Spaced-repetition decks for HSK vocabulary retention.", "skills": ["vocabulary"]},
    {"topic": "Mandarin", "type": "website", "name": "Chinese Grammar Wiki", "url": "https://resources.allsetlearning.com/chinese/grammar/", "level": "intermediate", "is_free": True, "description": "Comprehensive reference for Chinese grammar points by HSK level.", "skills": ["grammar", "reading"]},
    # --- Japanese ---
    {"topic": "Japanese", "type": "website", "name": "Tofugu — Learn Japanese", "url": "https://www.tofugu.com/learn-japanese/", "level": "beginner", "is_free": True, "description": "Guides to hiragana, katakana, kanji, and study strategy.", "skills": ["reading", "vocabulary"]},
    {"topic": "Japanese", "type": "website", "name": "Tae Kim's Guide to Japanese", "url": "https://guidetojapanese.org/learn/", "level": "beginner", "is_free": True, "description": "Clear grammar guide covering core Japanese sentence structure.", "skills": ["grammar", "reading"]},
    {"topic": "Japanese", "type": "website", "name": "NHK Easy News", "url": "https://www3.nhk.or.jp/news/easy/", "level": "intermediate", "is_free": True, "description": "Simplified Japanese news for reading and listening practice.", "skills": ["reading", "listening"]},
    {"topic": "Japanese", "type": "app", "name": "WaniKani", "url": "https://www.wanikani.com/", "level": "beginner", "is_free": True, "description": "Kanji and vocabulary SRS (first levels free).", "skills": ["vocabulary", "reading"]},
    {"topic": "Japanese", "type": "app", "name": "Anki + Core decks", "url": "https://ankiweb.net/shared/decks?search=japanese", "level": "beginner", "is_free": True, "description": "Core Japanese vocabulary decks with audio.", "skills": ["vocabulary", "listening"]},
    # --- Data Science ---
    {"topic": "Data Science", "type": "website", "name": "Kaggle Learn", "url": "https://www.kaggle.com/learn", "level": "beginner", "is_free": True, "description": "Short, practical courses on Python, pandas, ML, and SQL.", "skills": ["data analysis", "machine learning"]},
    {"topic": "Data Science", "type": "video", "name": "StatQuest (YouTube)", "url": "https://www.youtube.com/@statquest", "level": "beginner", "is_free": True, "description": "Intuitive explanations of statistics and machine learning concepts.", "skills": ["statistics", "machine learning"]},
    {"topic": "Data Science", "type": "website", "name": "fast.ai Practical Deep Learning", "url": "https://course.fast.ai/", "level": "intermediate", "is_free": True, "description": "Top-down deep learning course for coders.", "skills": ["machine learning", "deep learning"]},
    {"topic": "Data Science", "type": "website", "name": "pandas Documentation", "url": "https://pandas.pydata.org/docs/", "level": "intermediate", "is_free": True, "description": "Official pandas reference for data manipulation.", "skills": ["data analysis"]},
    {"topic": "Data Science", "type": "website", "name": "scikit-learn User Guide", "url": "https://scikit-learn.org/stable/user_guide.html", "level": "intermediate", "is_free": True, "description": "Guide to classical machine learning with scikit-learn.", "skills": ["machine learning"]},
    # --- SQL ---
    {"topic": "SQL", "type": "website", "name": "SQLBolt", "url": "https://sqlbolt.com/", "level": "beginner", "is_free": True, "description": "Interactive lessons to learn SQL queries step by step.", "skills": ["database", "querying"]},
    {"topic": "SQL", "type": "website", "name": "Mode SQL Tutorial", "url": "https://mode.com/sql-tutorial/", "level": "intermediate", "is_free": True, "description": "Analyst-focused SQL tutorial with real datasets.", "skills": ["database", "data analysis"]},
    {"topic": "SQL", "type": "website", "name": "SQLZoo", "url": "https://sqlzoo.net/", "level": "beginner", "is_free": True, "description": "Hands-on SQL exercises with instant feedback.", "skills": ["database"]},
    # --- AWS / Cloud ---
    {"topic": "AWS", "type": "website", "name": "AWS Skill Builder", "url": "https://skillbuilder.aws/", "level": "beginner", "is_free": True, "description": "Official AWS learning paths and free digital courses.", "skills": ["cloud", "devops"]},
    {"topic": "AWS", "type": "video", "name": "freeCodeCamp — AWS Certified Cloud Practitioner", "url": "https://www.youtube.com/watch?v=SOTamWNgDKc", "level": "beginner", "is_free": True, "description": "Full course preparing for the AWS Cloud Practitioner exam.", "skills": ["cloud"]},
    {"topic": "AWS", "type": "website", "name": "AWS Well-Architected Framework", "url": "https://aws.amazon.com/architecture/well-architected/", "level": "intermediate", "is_free": True, "description": "Best practices for designing reliable cloud systems.", "skills": ["cloud", "architecture"]},
    # --- Excel ---
    {"topic": "Excel", "type": "website", "name": "Exceljet", "url": "https://exceljet.net/", "level": "beginner", "is_free": True, "description": "Short, practical Excel formula and function guides.", "skills": ["spreadsheets", "data analysis"]},
    {"topic": "Excel", "type": "website", "name": "Microsoft Excel Training", "url": "https://support.microsoft.com/en-us/excel", "level": "beginner", "is_free": True, "description": "Official Microsoft Excel help and training videos.", "skills": ["spreadsheets"]},
    {"topic": "Excel", "type": "video", "name": "Leila Gharani (YouTube)", "url": "https://www.youtube.com/@LeilaGharani", "level": "intermediate", "is_free": True, "description": "Excel and Power BI tips for productivity and analytics.", "skills": ["spreadsheets", "data analysis"]},
    # --- Public Speaking ---
    {"topic": "Public Speaking", "type": "website", "name": "Toastmasters International", "url": "https://www.toastmasters.org/", "level": "beginner", "is_free": True, "description": "Structured practice and feedback for public speaking.", "skills": ["speaking", "confidence"]},
    {"topic": "Public Speaking", "type": "course", "name": "Coursera — Public Speaking", "url": "https://www.coursera.org/courses?query=public%20speaking", "level": "beginner", "is_free": True, "description": "University courses on speaking and presentation skills (audit free).", "skills": ["speaking", "presentation"]},
    # --- Spanish ---
    {"topic": "Spanish", "type": "app", "name": "Duolingo Spanish", "url": "https://www.duolingo.com/course/es/en/Learn-Spanish", "level": "beginner", "is_free": True, "description": "Gamified daily Spanish practice for vocabulary and grammar.", "skills": ["vocabulary", "listening"]},
    {"topic": "Spanish", "type": "website", "name": "SpanishDict", "url": "https://www.spanishdict.com/", "level": "beginner", "is_free": True, "description": "Dictionary, conjugation, and grammar reference.", "skills": ["grammar", "vocabulary"]},
    {"topic": "Spanish", "type": "video", "name": "Butterfly Spanish (YouTube)", "url": "https://www.youtube.com/@ButterflySpanish", "level": "beginner", "is_free": True, "description": "Friendly Spanish lessons focused on real conversation.", "skills": ["listening", "speaking"]},
    # --- Web Development ---
    {"topic": "Web Development", "type": "website", "name": "The Odin Project", "url": "https://www.theodinproject.com/", "level": "beginner", "is_free": True, "description": "Full-stack web development curriculum, project-based.", "skills": ["html", "css", "javascript", "web development"]},
    {"topic": "Web Development", "type": "website", "name": "freeCodeCamp", "url": "https://www.freecodecamp.org/learn/", "level": "beginner", "is_free": True, "description": "Free certifications in responsive web design and front-end.", "skills": ["html", "css", "javascript"]},
    {"topic": "Web Development", "type": "website", "name": "Next.js Learn", "url": "https://nextjs.org/learn", "level": "intermediate", "is_free": True, "description": "Official Next.js course building a full-stack app.", "skills": ["react", "web development"]},
    {"topic": "Web Development", "type": "website", "name": "Full Stack Open", "url": "https://fullstackopen.com/en/", "level": "intermediate", "is_free": True, "description": "Deep dive into modern React, Node.js, and GraphQL.", "skills": ["react", "node.js", "web development"]},
    # --- UX Design ---
    {"topic": "UX Design", "type": "website", "name": "Nielsen Norman Group Articles", "url": "https://www.nngroup.com/articles/", "level": "beginner", "is_free": True, "description": "Research-based articles on usability and UX principles.", "skills": ["ux research", "design"]},
    {"topic": "UX Design", "type": "course", "name": "Coursera — Google UX Design", "url": "https://www.coursera.org/professional-certificates/google-ux-design", "level": "beginner", "is_free": True, "description": "Professional UX certificate covering the design process (audit free).", "skills": ["ux research", "design", "prototyping"]},
    {"topic": "UX Design", "type": "tool", "name": "Figma", "url": "https://www.figma.com/", "level": "beginner", "is_free": True, "description": "Collaborative interface design and prototyping tool (free tier).", "skills": ["prototyping", "design"]},
    # --- German ---
    {"topic": "German", "type": "website", "name": "Deutsche Welle — Learn German", "url": "https://learngerman.dw.com/en/overview", "level": "beginner", "is_free": True, "description": "Free A1–C1 German courses with audio and placement test.", "skills": ["listening", "reading", "vocabulary"]},
    {"topic": "German", "type": "app", "name": "Anki + Goethe decks", "url": "https://ankiweb.net/shared/decks?search=german", "level": "beginner", "is_free": True, "description": "Vocabulary decks aligned with Goethe-Institut levels.", "skills": ["vocabulary"]},
    # --- Guitar ---
    {"topic": "Guitar", "type": "website", "name": "JustinGuitar", "url": "https://www.justinguitar.com/", "level": "beginner", "is_free": True, "description": "Structured, beginner-friendly guitar courses and lessons.", "skills": ["chords", "strumming"]},
    {"topic": "Guitar", "type": "video", "name": "Marty Music (YouTube)", "url": "https://www.youtube.com/@MartyMusic", "level": "beginner", "is_free": True, "description": "Song tutorials and technique lessons for guitar.", "skills": ["chords", "technique"]},
]


def _resource_embedding_text(item: dict) -> str:
    # Gabungkan field penting menjadi satu teks untuk di-embed.
    parts = [
        item.get("name", ""),
        item.get("topic", ""),
        item.get("description", ""),
        " ".join(item.get("skills", [])),
        item.get("level", ""),
    ]
    return ". ".join(part for part in parts if part)


def seed_resources(force: bool = False) -> int:
    # Seed resource berkualitas (idempoten: lewati yang namanya sudah ada).
    with SessionLocal() as db:
        existing_names = set(db.scalars(select(Resource.name)).all())
        to_add = [
            item for item in RESOURCE_SEED if force or item["name"] not in existing_names
        ]
        if not to_add:
            logger.info("Seed resource: tidak ada data baru.")
            return 0

        texts = [_resource_embedding_text(item) for item in to_add]
        vectors = generate_embeddings(texts)

        for item, vector in zip(to_add, vectors, strict=True):
            db.add(
                Resource(
                    topic=item["topic"],
                    type=item["type"],
                    name=item["name"],
                    url=item.get("url"),
                    level=item.get("level"),
                    is_free=item.get("is_free", True),
                    description=item.get("description"),
                    skills=item.get("skills", []),
                    embedding=vector,
                )
            )
        db.commit()
        logger.info("Seed resource: %d resource ditambahkan.", len(to_add))
        return len(to_add)


def _relevance_label(score: float | None) -> str | None:
    # high (>=0.6) / medium (0.4-0.6) / low (<0.4).
    if score is None:
        return None
    if score >= 0.6:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


def _to_response(resource: Resource, similarity: float | None = None) -> ResourceResponse:
    return ResourceResponse(
        id=resource.id,
        topic=resource.topic,
        type=resource.type,
        name=resource.name,
        url=resource.url,
        level=resource.level,
        is_free=resource.is_free,
        description=resource.description,
        skills=resource.skills or [],
        similarity_score=round(similarity, 4) if similarity is not None else None,
        relevance_label=_relevance_label(similarity),
    )


def _topic_adjust(resource_topic: str, prefer_topic: str | None) -> float:
    # Boost kalau topic cocok, penalti kalau berbeda (mis. IELTS vs TOEFL).
    if not prefer_topic:
        return 0.0
    resource_lower = resource_topic.lower()
    prefer_lower = prefer_topic.lower()
    if resource_lower == prefer_lower or resource_lower in prefer_lower or prefer_lower in resource_lower:
        return TOPIC_BOOST
    return -TOPIC_MISMATCH_PENALTY


def search_resources(
    query: str,
    topic: str | None = None,
    level: str | None = None,
    top_k: int = 10,
    min_similarity: float | None = None,
    prefer_topic: str | None = None,
) -> list[ResourceResponse]:
    # Semantic search: ambil kandidat, sesuaikan skor dengan topic match, lalu urutkan.
    text = (query or topic or "").strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide a query or topic.",
        )
    query_vector = generate_embedding(text)
    fetch_k = max(top_k * 3, 30)

    with SessionLocal() as db:
        distance = Resource.embedding.cosine_distance(query_vector).label("distance")
        stmt = select(Resource, distance).where(Resource.embedding.isnot(None))
        if topic:
            stmt = stmt.where(Resource.topic.ilike(f"%{topic}%"))
        if level:
            stmt = stmt.where(Resource.level == level)
        stmt = stmt.order_by(distance).limit(fetch_k)
        rows = db.execute(stmt).all()

    scored: list[tuple[Resource, float]] = []
    for resource, dist in rows:
        base = 1.0 - float(dist)
        adjusted = max(0.0, min(1.0, base + _topic_adjust(resource.topic, prefer_topic)))
        scored.append((resource, adjusted))
    scored.sort(key=lambda item: item[1], reverse=True)

    results = [_to_response(resource, score) for resource, score in scored]
    if min_similarity is not None:
        results = [r for r in results if (r.similarity_score or 0.0) >= min_similarity]
    results = results[:top_k]
    logger.info(
        "Search resource: query=%r topic=%s level=%s prefer=%s hasil=%d",
        text,
        topic,
        level,
        prefer_topic,
        len(results),
    )
    return results


def _get_owned_plan(db: Session, user_id: uuid.UUID, plan_id: uuid.UUID) -> StudyPlan:
    plan = db.scalar(
        select(StudyPlan).where(StudyPlan.id == plan_id, StudyPlan.user_id == user_id)
    )
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found.")
    return plan


def recommend_for_plan(
    user_id: uuid.UUID,
    plan_id: uuid.UUID,
    top_k: int = 8,
    min_similarity: float = 0.4,
) -> list[ResourceResponse]:
    # Rekomendasi resource berdasarkan topik & tujuan plan (+ threshold relevansi).
    with SessionLocal() as db:
        plan = _get_owned_plan(db, user_id, plan_id)
        goal = db.get(Goal, plan.goal_id)
        summary = (plan.plan_data or {}).get("goal_summary", "")

    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found.")

    query = ". ".join(
        part
        for part in [
            goal.topic,
            f"Target: {goal.target}" if goal.target else "",
            f"Level: {goal.current_level}" if goal.current_level else "",
            summary,
        ]
        if part
    )
    # Ambil kandidat lebih banyak, boost topic match dengan topik goal.
    candidates = search_resources(
        query=query, prefer_topic=goal.topic, top_k=max(top_k * 3, 24)
    )

    filtered = [r for r in candidates if (r.similarity_score or 0.0) >= min_similarity]
    if len(filtered) < 5:
        # Fallback: turunkan threshold ke 0.3, atau ambil 5 teratas.
        relaxed = [r for r in candidates if (r.similarity_score or 0.0) >= 0.3]
        filtered = relaxed if len(relaxed) >= 5 else candidates[:5]

    logger.info(
        "Recommend resource: plan_id=%s topic=%r hasil=%d (min_similarity=%.2f)",
        plan_id,
        goal.topic,
        len(filtered),
        min_similarity,
    )
    return filtered[:top_k]
