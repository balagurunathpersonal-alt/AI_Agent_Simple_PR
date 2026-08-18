from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Recommendation(str, Enum):
    APPROVE = "APPROVE"
    APPROVE_WITH_COMMENTS = "APPROVE_WITH_COMMENTS"
    REQUEST_CHANGES = "REQUEST_CHANGES"


class FindingSource(str, Enum):
    STATIC_ANALYZER = "STATIC_ANALYZER"
    AI_REVIEW = "AI_REVIEW"


class ReviewFinding(BaseModel):
    severity: Severity

    category: str

    file: str

    line_number: Optional[int] = None

    title: str

    explanation: str

    why_it_matters: str

    suggested_fix: str

    source: FindingSource


class PRReviewResult(BaseModel):
    pr_summary: str

    overall_risk: Severity

    files_reviewed: list[str] = Field(
        default_factory=list
    )

    findings: list[ReviewFinding] = Field(
        default_factory=list
    )

    testing_recommendations: list[str] = Field(
        default_factory=list
    )

    final_recommendation: Recommendation