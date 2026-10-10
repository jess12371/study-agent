# Service F-08 — Export study plan ke PDF (reportlab) dan iCalendar (icalendar).
# Library berat (reportlab/icalendar) di-import lazy agar startup app cepat.

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, time, timedelta, timezone
from io import BytesIO

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.goal import Goal
from app.models.study_plan import StudyPlan

logger = logging.getLogger(__name__)

DEFAULT_SESSION_TIME = "19:00"


def _get_owned_plan(db: Session, user_id: uuid.UUID, plan_id: uuid.UUID) -> StudyPlan:
    # 404 (bukan 403) agar keberadaan plan user lain tidak bocor.
    plan = db.scalar(
        select(StudyPlan).where(StudyPlan.id == plan_id, StudyPlan.user_id == user_id)
    )
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found.")
    return plan


# ---------------------------------------------------------------- PDF


def _styles() -> dict[str, "ParagraphStyle"]:
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "SATitle", parent=base["Title"], fontName="Helvetica-Bold", fontSize=20,
            leading=24, textColor=colors.HexColor("#111827"), alignment=0, spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "SASubtitle", parent=base["Normal"], fontName="Helvetica", fontSize=10,
            leading=14, textColor=colors.HexColor("#6b7280"),
        ),
        "heading": ParagraphStyle(
            "SAHeading", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=13,
            leading=16, textColor=colors.HexColor("#111827"), spaceBefore=14, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "SABody", parent=base["Normal"], fontName="Helvetica", fontSize=10,
            leading=14, textColor=colors.HexColor("#1f2937"),
        ),
        "muted": ParagraphStyle(
            "SAMuted", parent=base["Normal"], fontName="Helvetica", fontSize=9,
            leading=12, textColor=colors.HexColor("#6b7280"),
        ),
        "session": ParagraphStyle(
            "SASession", parent=base["Normal"], fontName="Helvetica", fontSize=9.5,
            leading=13, textColor=colors.HexColor("#374151"),
        ),
    }


def _footer(canvas, doc) -> None:
    # Footer sederhana di tiap halaman.
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm

    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#9ca3af"))
    canvas.drawString(18 * mm, 12 * mm, "Study Agent — AI-Powered Study Plans")
    canvas.drawRightString(A4[0] - 18 * mm, 12 * mm, f"Page {doc.page}")
    canvas.restoreState()


def export_plan_to_pdf(user_id: uuid.UUID, plan_id: uuid.UUID) -> bytes:
    # Bangun PDF A4 print-friendly dari plan_data.
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        ListFlowable,
        ListItem,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    with SessionLocal() as db:
        plan = _get_owned_plan(db, user_id, plan_id)
        data = plan.plan_data or {}
        goal = db.get(Goal, plan.goal_id)
        created_at = plan.created_at or datetime.now(timezone.utc)

    styles = _styles()
    story: list = []

    # Header
    story.append(Paragraph("Study Agent — Study Plan", styles["title"]))
    story.append(
        Paragraph(
            f"Generated {created_at:%d %b %Y} · {data.get('total_weeks', '?')} weeks",
            styles["subtitle"],
        )
    )
    story.append(Spacer(1, 10))

    if goal is not None:
        meta_rows = [
            ["Topic", goal.topic or "—"],
            ["Target", goal.target or "—"],
            ["Current level", goal.current_level or "—"],
            ["Deadline", f"{goal.deadline_months} months" if goal.deadline_months else "—"],
            [
                "Availability",
                (
                    f"{goal.work_hours_start:%H:%M}–{goal.work_hours_end:%H:%M}"
                    if goal.work_hours_start and goal.work_hours_end
                    else "—"
                ),
            ],
        ]
        table = Table(meta_rows, colWidths=[35 * mm, 140 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#374151")),
                    ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#111827")),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("LINEBELOW", (0, 0), (-1, -2), 0.25, colors.HexColor("#e5e7eb")),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 6))

    story.append(Paragraph("Summary", styles["heading"]))
    story.append(Paragraph(data.get("goal_summary") or "—", styles["body"]))

    # Milestones
    milestones = data.get("milestones", [])
    if milestones:
        story.append(Paragraph("Milestones", styles["heading"]))
        for milestone in milestones:
            story.append(
                Paragraph(
                    f"<b>Month {milestone.get('month', '?')}</b> — {milestone.get('focus', '')}",
                    styles["body"],
                )
            )
            story.append(
                Paragraph(f"Target: {milestone.get('target', '—')}", styles["session"])
            )
            story.append(
                Paragraph(f"Checkpoint: {milestone.get('checkpoint', '—')}", styles["session"])
            )
            story.append(Spacer(1, 4))

    # Weekly schedule
    weeks = data.get("weekly_schedule", [])
    if weeks:
        story.append(Paragraph("Weekly Schedule", styles["heading"]))
        for week in weeks:
            story.append(
                Paragraph(
                    f"Week {week.get('week', '?')} — {week.get('theme', '')}",
                    styles["body"],
                )
            )
            for session in week.get("days", []):
                activities = session.get("activities", []) or []
                line = (
                    f"<b>{session.get('day', '')} {session.get('time', '')}</b> — "
                    f"{session.get('topic', '')} "
                    f"({session.get('duration_minutes', 0)} min)"
                )
                story.append(Paragraph(line, styles["session"]))
                if activities:
                    story.append(
                        ListFlowable(
                            [
                                ListItem(Paragraph(a, styles["muted"]), leftIndent=12)
                                for a in activities
                            ],
                            bulletType="bullet",
                            start="•",
                            leftIndent=14,
                        )
                    )
            story.append(Spacer(1, 6))

    # Resources
    resources = data.get("resources", [])
    if resources:
        story.append(Paragraph("Resources", styles["heading"]))
        for resource in resources:
            name = resource.get("name", "")
            url = resource.get("url") or ""
            meta = " · ".join(
                str(part)
                for part in [resource.get("type"), resource.get("for_skill")]
                if part
            )
            text = f"<b>{name}</b>"
            if meta:
                text += f" <font color='#6b7280'>({meta})</font>"
            if url:
                text += f"<br/><font color='#2563eb' size='8'>{url}</font>"
            story.append(Paragraph(text, styles["session"]))
            story.append(Spacer(1, 3))

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
        title="Study Agent — Study Plan",
        author="Study Agent",
    )
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    logger.info("PDF diexport: plan_id=%s bytes=%d", plan_id, buffer.tell())
    return buffer.getvalue()


# ---------------------------------------------------------------- ICS


def _parse_time(value: str | None) -> time:
    # Parse "HH:MM" → datetime.time. Fallback ke DEFAULT_SESSION_TIME.
    text = value or DEFAULT_SESSION_TIME
    try:
        hours, minutes = text.split(":")[:2]
        return time(int(hours), int(minutes))
    except (ValueError, AttributeError):
        return time(19, 0)


def export_plan_to_ics(user_id: uuid.UUID, plan_id: uuid.UUID) -> str:
    # Bangun kalender iCalendar; tiap sesi jadi satu VEVENT.
    from icalendar import Calendar, Event

    with SessionLocal() as db:
        plan = _get_owned_plan(db, user_id, plan_id)
        data = plan.plan_data or {}
        base_date: date = plan.created_at.date() if plan.created_at else date.today()

    calendar = Calendar()
    calendar.add("prodid", "-//Study Agent//Study Plan//EN")
    calendar.add("version", "2.0")
    calendar.add("calscale", "GREGORIAN")
    calendar.add("x-wr-calname", "Study Agent — Study Plan")

    stamp = datetime.now(timezone.utc)
    count = 0
    for week in data.get("weekly_schedule", []):
        for index, session in enumerate(week.get("days", [])):
            offset = session.get("date_offset")
            if offset is None:
                offset = (week.get("week", 1) - 1) * 7 + index
            start = datetime.combine(
                base_date + timedelta(days=int(offset)), _parse_time(session.get("time"))
            )
            end = start + timedelta(minutes=session.get("duration_minutes") or 30)

            event = Event()
            event.add("uid", f"{plan_id}-w{week.get('week')}-{index}@study-agent")
            event.add("dtstamp", stamp)
            event.add("dtstart", start)
            event.add("dtend", end)
            event.add("summary", f"[Study] {session.get('topic', 'Study session')}")
            description_parts = list(session.get("activities", []) or [])
            for resource in session.get("resources", []) or []:
                if isinstance(resource, dict) and resource.get("name"):
                    url = resource.get("url")
                    description_parts.append(
                        f"Resource: {resource['name']}" + (f" ({url})" if url else "")
                    )
            event.add(
                "description",
                "\n".join(description_parts) if description_parts else "Study session",
            )
            calendar.add_component(event)
            count += 1

    logger.info("ICS diexport: plan_id=%s events=%d", plan_id, count)
    return calendar.to_ical().decode("utf-8")
