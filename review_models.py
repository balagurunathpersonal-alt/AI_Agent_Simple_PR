from enum import Enum
from typing import List, Optional

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


class ReviewFinding(BaseModel):
    severity: Severity

    category: str

    file: str

    line_number: Optional[int] = None

    title: str

    explanation: str

    why_it_matters: str

    suggested_fix: str


class PRReviewResult(BaseModel):
    pr_summary: str

    overall_risk: Severity

    files_reviewed: List[str] = Field(
        default_factory=list
    )

    findings: List[ReviewFinding] = Field(
        default_factory=list
    )

    testing_recommendations: List[str] = Field(
        default_factory=list
    )

    final_recommendation: Recommendation