# Package skema Pydantic.
from app.schemas.auth import TokenResponse, UserLogin, UserRegister, UserResponse
from app.schemas.chat import (
    ChatAction,
    ChatActionRequest,
    ChatActionResult,
    ChatHistoryResponse,
    ChatMessage,
    ChatRequest,
    ChatResponse,
)
from app.schemas.feasibility import FeasibilityRequest, FeasibilityResponse, RescopeRequest, RescopeSuggestion
from app.schemas.goal import GoalCreate, GoalResponse, GoalUpdate
from app.schemas.llm import LLMRequest, LLMResponse, TokenUsage
from app.schemas.plan import (
    DaySession,
    Milestone,
    PlanGenerateRequest,
    PlanNextMonthRequest,
    PlanRequest,
    PlanResponse,
    PlanVersion,
    Resource,
    WeekSchedule,
)
from app.schemas.progress import (
    ProgressEntry,
    ProgressMark,
    ProgressStats,
    ProgressUpdate,
)
from app.schemas.reschedule import (
    RescheduleAnalysis,
    RescheduleOption,
    RescheduleRequest,
    RescheduleResult,
)
from app.schemas.resource import (
    ResourceCreate,
    ResourceResponse,
    ResourceSearchRequest,
)
from app.schemas.tutor import QuizQuestion, QuizResponse, TutorMessage, TutorRequest
from app.schemas.quiz import (
    QuizAttemptResponse,
    QuizHistoryResponse,
    QuizSubmitRequest,
)

__all__ = [
    # LLM
    "LLMRequest",
    "LLMResponse",
    "TokenUsage",
    # Feasibility (F-02)
    "FeasibilityRequest",
    "FeasibilityResponse",
    "RescopeRequest",
    "RescopeSuggestion",
    # Plan (F-03)
    "PlanRequest",
    "PlanGenerateRequest",
    "PlanNextMonthRequest",
    "PlanResponse",
    "PlanVersion",
    "Milestone",
    "DaySession",
    "WeekSchedule",
    "Resource",
    # Goals (F-01)
    "GoalCreate",
    "GoalUpdate",
    "GoalResponse",
    # Auth (F-09)
    "UserRegister",
    "UserLogin",
    "UserResponse",
    "TokenResponse",
    # Progress (F-04)
    "ProgressUpdate",
    "ProgressMark",
    "ProgressEntry",
    "ProgressStats",
    # Reschedule (F-05)
    "RescheduleAnalysis",
    "RescheduleOption",
    "RescheduleRequest",
    "RescheduleResult",
    # Resources (F-06)
    "ResourceCreate",
    "ResourceResponse",
    "ResourceSearchRequest",
    # Chat (F-11)
    "ChatAction",
    "ChatActionRequest",
    "ChatActionResult",
    "ChatHistoryResponse",
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    # Tutor
    "TutorMessage",
    "TutorRequest",
    "QuizQuestion",
    "QuizResponse",
    # Gamifikasi quiz
    "QuizSubmitRequest",
    "QuizAttemptResponse",
    "QuizHistoryResponse",
]
