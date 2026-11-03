"""Public, unauthenticated endpoints for shared review summaries."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from api.schemas.review import FeedbackSection, PublicReviewSummary
from core.database import get_db
from core.services.share_service import get_shared_review

log = structlog.get_logger()

router = APIRouter(prefix="/share", tags=["share"])


@router.get("/{token}", response_model=PublicReviewSummary)
async def get_shared_review_endpoint(
    token: str,
    db=Depends(get_db),
):
    """
    Retrieve a read-only review summary using a public share token.

    Does not require authentication. Returns 404 for unknown tokens and
    410 when the link has expired.
    """
    try:
        review, share_link = await get_shared_review(db=db, token=token)

        sections = None
        if review.sections:
            sections = [FeedbackSection.model_validate(s) for s in review.sections]

        return PublicReviewSummary(
            status=review.status,
            overall_score=review.overall_score,
            sections=sections,
            expires_at=share_link.expires_at,
        )
    except HTTPException:
        raise
    except Exception as exc:
        log.error("get_shared_review_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve shared review",
        )
