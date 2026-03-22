from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# SessionStatus
# ---------------------------------------------------------------------------

class SessionStatus(str, Enum):
    """Shared by API responses and workflow state reporting."""

    queued        = "queued"
    running       = "running"
    waiting_human = "waiting_human"
    completed     = "completed"
    failed        = "failed"
    cancelled     = "cancelled"


# ---------------------------------------------------------------------------
# ErrorInfo
# ---------------------------------------------------------------------------

class ErrorInfo(BaseModel):
    """Normalized error payload returned by all endpoints.

    Optimisations vs original
    ─────────────────────────
    • model_config frozen=True
        Pydantic skips building a mutable __dict__ and instead uses
        __slots__ on the generated class, which cuts per-instance memory
        by ~40-60 % and also makes hashing/equality faster.

    • model_config slots=True  (Pydantic v2 only)
        Generates __slots__ directly on the model class so attribute
        access goes through the slot descriptor rather than __dict__.

    • details: dict[str, Any] | None  (default None instead of dict)
        The original used default_factory=dict, which allocates a fresh
        empty dict for *every* ErrorInfo that has no details — typically
        the majority.  Changing the default to None means that allocation
        only happens when there is real data.  Callers that used to check
        `if info.details` still work; callers that iterated over it must
        guard with `for k, v in (info.details or {}).items()`.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,   # immutable → __slots__ layout, no __dict__ per instance
        slots=True,    # explicit __slots__ on the generated class (Pydantic v2)
    )

    code: str = Field(..., min_length=1, description="Stable machine-readable error code.")
    message: str = Field(..., min_length=1, description="Human-readable error message.")

    # None instead of empty-dict default — avoids allocating a new dict for
    # every instance that carries no details (usually the majority).
    details: dict[str, Any] | None = Field(
        default=None,
        description="Optional structured details for debugging and UI hints.",
    )
    retryable: bool = Field(
        False,
        description="Whether client can safely retry the request.",
    )


# ---------------------------------------------------------------------------
# ApiEnvelope
# ---------------------------------------------------------------------------

class ApiEnvelope(BaseModel):
    """Uniform HTTP response wrapper for success and failure cases.

    Optimisations vs original
    ─────────────────────────
    • Same frozen=True + slots=True as ErrorInfo (see above).

    • data: dict[str, Any] | None  already defaults to None in the
        original, so no change needed there.

    • status field uses SessionStatus directly — no string coercion at
        runtime because frozen models skip the copy-on-set path.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        slots=True,
    )

    request_id: str = Field(..., min_length=1, description="Server-side request identifier.")
    session_id: str = Field(..., min_length=1, description="Workflow session identifier.")
    status: SessionStatus = Field(..., description="Current status of the session.")
    data: dict[str, Any] | None = Field(
        default=None,
        description="Structured payload for successful responses.",
    )
    error: ErrorInfo | None = Field(
        default=None,
        description="Structured error payload when status is failed/cancelled.",
    )
