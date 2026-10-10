PRD — Study Agent
Version: 2.1 (English Output)
Date: 2026-10-09
Platform: Web Application
LLM: DeepSeek V4.1 Flash (via OpenCode)
Output Language: English (v1)

1. Product Summary
Study Agent is a web-based AI agent that helps users create personalized study schedules based on their goals, deadlines, and work hours.

User input: topic, target, deadline, work hours, preferred study time.
Agent output: daily/weekly schedule + material syllabus + monthly milestones + resources.

Example:

"Learn Mandarin from scratch → HSK 4 score 250 in 6 months. Work 9 AM–6 PM, Mon–Fri."
→ Agent generates study schedule outside work hours + weekly material breakdown.

2. Problem Statement
Users don't know where to start learning

No clear order of materials

Schedules don't fit with work hours

No progress tracking

Learning resources are scattered

3. Goals & Success Metrics
Goals:

Generate personalized study plan in < 60 seconds

Feasibility check before generating plan

Actionable weekly syllabus

Progress tracking

Adaptive reschedule (v1.1)

Success Metrics:

Metric	Target
Plan generation success	> 95%
Onboarding completion	> 70%
Time estimation accuracy	Deviation < 20%
30-day retention	> 40%
User satisfaction	> 4/5
LLM cost per user/month	< $0.01
4. Target Users
Persona	Description	Need
Professional up-skiller	25–35 y/o, full-time employee	Flexible schedule outside work
Student	18–24 y/o, certification target	Clear material roadmap
Career switcher	28–40 y/o, changing field	Realistic estimate & milestones
5. User Stories
US-01: Input learning goal (topic, target, deadline)

US-02: Input work hours & daily availability

US-03: View feasibility check result

US-04: View daily/weekly study schedule

US-05: View weekly material syllabus

US-06: Mark progress (done/skip)

US-07: Get learning resource recommendations

US-08: Agent adjusts schedule if falling behind

US-09: Get study reminders

US-10: Export schedule to PDF/Calendar

6. Features (MVP)
ID	Feature	Priority	LLM?
F-01	Onboarding input	P0	No
F-02	Feasibility check	P0	Yes (high)
F-03	Study plan generator	P0	Yes (high)
F-04	Progress tracker	P0	No
F-05	Adaptive reschedule	P1	Yes (medium)
F-06	Resource recommendation	P1	Yes (low)
F-07	Reminder & notification	P2	No
F-08	Export plan	P2	No
F-09	User authentication	P0	No
F-10	Plan history	P1	No
Key Feature Details
F-02: Feasibility Check

Agent analyzes if target is realistic given available time

Compare required hours vs available hours

Output: verdict + confidence + recommendations

Must cite benchmark or mark as "estimate"

F-03: Study Plan Generator

Breakdown target → sub-skills → monthly milestones → weekly schedule

Allocate to user's free time (outside work hours)

Include resources per topic

Output: valid JSON

F-04: Progress Tracker

User marks: done / skip / reschedule

Dashboard: completion rate, total hours, streak

7. Non-Functional Requirements
Category	Requirement
Performance	Plan generation < 30 seconds
Scalability	1,000 concurrent users (MVP)
Availability	Uptime 99%
Security	JWT + OAuth, TLS 1.3
Cost	LLM < $0.10/user/month
Language	English (v1)
8. Architecture
System flow:

Web Browser (Next.js + Tailwind)
↓
API Gateway (FastAPI)
↓
Agent Orchestrator (LangGraph)
↓
DeepSeek V4.1 Flash + PostgreSQL + pgvector

Components:

Layer	Technology
Frontend	Next.js 14 + Tailwind + shadcn/ui
Backend	FastAPI (Python)
Agent Framework	LangGraph
LLM	DeepSeek V4.1 Flash
Database	PostgreSQL 16
Vector DB	pgvector
Auth	Supabase Auth
Hosting FE	Vercel
Hosting BE	Railway / Fly.io
9. LLM Configuration — DeepSeek V4.1 Flash
Model: deepseek-flash
Base URL: https://api.deepseek.com
Context Window: 1,000,000 tokens
Max Output: 384,000 tokens
Features: JSON Mode, Function Calling, Thinking Mode, Context Caching

Parameters per Task:

Task	reasoning_effort	thinking	temperature	max_tokens
Feasibility Check	high	enabled	0.7	4096
Plan Generation	high	enabled	0.7	8192
Resource Recommendation	low	disabled	0.3	2048
Adaptive Reschedule	medium	enabled	0.5	4096
Chat/Clarification	low	disabled	0.8	1024
Pricing:

Token Type	Off-Peak	Peak
Input (cache hit)	$0.003/1M	$0.006/1M
Input (cache miss)	$0.15/1M	$0.30/1M
Output	$0.60/1M	$1.20/1M
Context Caching: Put static content at the beginning of messages, variable content at the end. Save up to 90%.

10. Agent Behavior & Guardrails
Tone: English, friendly, motivating, realistic.

MUST:

Feasibility check before generating plan

Cite benchmark or mark as "estimate"

Output = valid JSON

If target unrealistic → give 2-3 alternatives

Validate resource URLs

DO NOT:

Medical/psychological advice

Promise exam passing

Paid resources without free alternatives

Fallback:

Scenario	Action
LLM timeout	Retry exponential backoff
Rate limit (429)	Queue + retry
Server error (500/503)	Fallback model
Invalid JSON	Repair prompt
Confidence < 0.6	Manual review
11. Data Model
Tables:

users — id, email, name, hashed_password, is_active, created_at, updated_at

goals — id, user_id, topic, current_level, target, deadline_months, work_hours_start, work_hours_end, work_days, preferred_study_time, max_session_minutes, unavailable_days, status

study_plans — id, goal_id, user_id, plan_data (JSONB), feasibility_data (JSONB), total_weeks, status

progress_entries — id, plan_id, week_number, day_name, session_index, status, actual_duration, difficulty_rating, notes, scheduled_at, completed_at

resources — id, topic, type, name, url, level, is_free, description, embedding (VECTOR 1536)

reminders — id, user_id, plan_id, type, scheduled_at, sent_at, status

12. API Endpoints (MVP)
Method	Endpoint	Description
POST	/api/auth/signup	Register
POST	/api/auth/login	Login
POST	/api/goals	Create goal
GET	/api/goals	List goals
POST	/api/feasibility/check	Check feasibility
POST	/api/plans/generate	Generate plan (SSE stream)
GET	/api/plans/:id	Get plan detail
PATCH	/api/plans/:id/progress	Update progress
13. Prompt Engineering
System Prompt (Feasibility Check):

text
You are Study Agent, an expert learning plan feasibility analyzer.

Your task: analyze if a learning goal is realistic given the user's 
available time and deadline.

RULES:
1. Cite benchmark sources when estimating required hours
2. If target unrealistic, provide 2-3 alternatives
3. Output MUST be valid JSON matching the schema
4. All text in English
5. Be supportive but realistic — don't over-promise

TONE: Supportive, realistic, motivating
System Prompt (Plan Generator):

text
You are Study Agent, an expert learning plan designer.

Your task: create a realistic, structured study plan based on the 
user's goal and constraints.

RULES:
1. ALWAYS check feasibility before generating plan
2. Cite benchmark sources when estimating hours
3. If target unrealistic, provide 2-3 alternatives
4. Breakdown target into monthly milestones
5. Create weekly schedule respecting work hours
6. Include specific resources per topic
7. Output MUST be valid JSON
8. All text in English

TONE: Supportive, realistic, motivating
User Prompt Template (Feasibility):

text
Analyze feasibility of this learning goal:

GOAL: {topic}
CURRENT LEVEL: {current_level}
TARGET: {target}
DEADLINE: {deadline_months} months
WORK HOURS: {work_hours_start}–{work_hours_end}
WORK DAYS: {work_days}
PREFERRED STUDY TIME: {preferred_study_time}
MAX SESSION: {max_session_minutes} minutes

Respond in JSON with:
- feasible (bool)
- confidence (0.0-1.0)
- required_hours (int)
- available_hours (int)
- gap_hours (int)
- verdict (REALISTIC / REALISTIC_WITH_NOTES / UNREALISTIC)
- analysis (string, in English)
- recommendations (list of strings, in English)
- benchmark_source (string or null)
User Prompt Template (Plan Generation):

text
Generate a complete study plan:

GOAL: {topic}
CURRENT LEVEL: {current_level}
TARGET: {target}
DEADLINE: {deadline_months} months
WORK HOURS: {work_hours_start}–{work_hours_end}
WORK DAYS: {work_days}
PREFERRED STUDY TIME: {preferred_study_time}
MAX SESSION: {max_session_minutes} minutes

Output JSON with:
- plan_id
- goal_summary
- total_weeks
- milestones (array)
- weekly_schedule (array)
- resources (array)

All text in English.
14. Timeline
Phase	Deliverable	Timeline
Research & Design	PRD, wireframe, benchmark	Week 1–2
Setup	API, OpenCode, DB schema	Week 2
MVP Development	F-01 to F-04, F-09	Week 3–6
Testing	QA, LLM eval	Week 7
Beta Launch	20–50 beta users	Week 8
Iteration	F-05, F-06	Week 9–10
Public Launch	v1.0	Week 11–12
15. Risks
Risk	Impact	Mitigation
LLM hallucination	High	RAG + citation + validation
Unrealistic target	High	Feasibility check
User dropout	Medium	Reminder + adaptive reschedule
LLM cost overrun	Medium	Caching + token limits
Data privacy	High	Encryption + compliance
16. Open Questions
Which topics supported in MVP?

Use OpenCode Zen or direct DeepSeek API?

Need fallback model?

Monetization: free/freemium/subscription?

Google Calendar integration in v1?

17. F-11: Agent Dialog

Context-aware chat between the user and Study Agent, scoped to a goal.

Capabilities:
- Answer questions about the plan (e.g. "Why is Week 3 hard?")
- Suggest plan modifications (rendered as action buttons)
- Discuss progress & motivation
- Recommend resources

Agent context: goal, latest plan (version), progress stats, and recent progress issues.

Multilingual:
- Auto-detect user language (English / Chinese)
- Respond in the same language
- Allow switching language between messages

Agent output = valid JSON: { message, actions[] }. Supported actions:
- modify_plan (REBALANCE / EXTEND / REDUCE / INTENSIFY / regenerate)
- view_resource (resource detail)

Rules:
- Auth required
- History stored per (user, goal); context limited to the last 20 messages
- Integrates with plan versioning (modify_plan creates a new version, old plan superseded)
- Supportive & realistic tone, responses < 200 words

Document End