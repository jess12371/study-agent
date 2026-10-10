# AGENTS.md — Study Agent

> Konteks project untuk OpenCode.

## Apa Ini
Study Agent = AI agent web yang bikin jadwal belajar personal
berdasarkan goal user, deadline, dan jam kerja.

Input: topik, target, deadline, jam kerja
Output: jadwal harian + silabus + milestone + resource

## Tech Stack
- Frontend: Next.js 14 + Tailwind
- Backend: FastAPI (Python)
- Agent: LangGraph
- LLM: DeepSeek V4.1 Flash (deepseek-flash)
- Database: PostgreSQL + pgvector

## Core Features (MVP)
- F-01: Onboarding input
- F-02: Feasibility check (LLM)
- F-03: Study plan generator (LLM)
- F-04: Progress tracker
- F-09: Auth

## Aturan Agent
- English (v1)
- WAJIB feasibility check sebelum generate plan
- WAJIB cite benchmark atau tandai "estimasi"
- Output = valid JSON
- Kalau target tidak realistis → kasih 2-3 alternatif

## LLM Config
- Model: deepseek-flash
- Base URL: https://api.deepseek.com
- Feasibility: reasoning_effort=high, thinking=enabled
- Plan Generation: reasoning_effort=high, thinking=enabled, stream=true
- Resource Rec: reasoning_effort=low, thinking=disabled

## PRD Lengkap
Lihat docs/PRD.md