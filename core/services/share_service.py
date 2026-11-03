"""Service for creating and resolving public review share links."""

from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from uuid import UUID

import structlog
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.models.review import Review
from core.models.review_share import ReviewShareLink
from core.services.review_service import get_review

log = structlog.get_logger()

SHARE_LINK_TTL_DAYS = 30
TOKEN_BYTE_LENGTH = 32


def _utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(UTC)


def _ensure_aware(value: datetime) -> datetime:
    """Normalize naive datetimes to UTC for safe comparison."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


async def _get_active_share_link(db, review_id: str) -> ReviewShareLink | None:
    """Return the newest unexpired share link for a review, if one exists."""
    now = _utcnow()
    stmt = (
        select(ReviewShareLink)
        .where(
            ReviewShareLink.review_id == review_id,
            ReviewShareLink.expires_at > now,
        )
        .order_by(ReviewShareLink.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def create_share_link(
    db,
    review_id: UUID,
    user_id: UUID,
) -> ReviewShareLink:
    """
    Return a shareable link for a completed review.

    Reuses the newest still-valid share link for the review when one exists.
    Otherwise creates a new cryptographically secure token that expires in
    30 days.

    Args:
        db: Async database session.
        review_id: Review to share.
        user_id: Authenticated owner of the review.

    Returns:
        An active ReviewShareLink (reused or newly created).

    Raises:
        HTTPException: If the review is missing, not owned, or not complete.
    """
    review = await get_review(db=db, review_id=review_id, user_id=user_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    if review.status != "complete":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only completed reviews can be shared",
        )

    existing = await _get_active_share_link(db, str(review.id))
    if existing:
        log.info(
            "share_link_reused",
            review_id=str(review_id),
            share_link_id=str(existing.id),
            expires_at=_ensure_aware(existing.expires_at).isoformat(),
        )
        return existing

    now = _utcnow()
    share_link = ReviewShareLink(
        token=token_urlsafe(TOKEN_BYTE_LENGTH),
        review_id=str(review.id),
        expires_at=now + timedelta(days=SHARE_LINK_TTL_DAYS),
        created_at=now,
    )
    db.add(share_link)
    await db.commit()
    await db.refresh(share_link)

    log.info(
        "share_link_created",
        review_id=str(review_id),
        share_link_id=str(share_link.id),
        expires_at=share_link.expires_at.isoformat(),
    )
    return share_link


async def get_shared_review(
    db,
    token: str,
) -> tuple[Review, ReviewShareLink]:
    """
    Resolve a public share token to its review summary.

    Args:
        db: Async database session.
        token: Opaque share token from the public URL.

    Returns:
        Tuple of (Review, ReviewShareLink) when the token is valid.

    Raises:
        HTTPException: For missing/invalid tokens (404) or expired links (410).
    """
    if not token or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found",
        )

    stmt = (
        select(ReviewShareLink)
        .options(selectinload(ReviewShareLink.review))
        .where(ReviewShareLink.token == token)
    )
    result = await db.execute(stmt)
    share_link = result.scalars().first()

    if not share_link or not share_link.review:
        log.warning("share_link_not_found", token_prefix=token[:8] if token else "")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found",
        )

    if _ensure_aware(share_link.expires_at) < _utcnow():
        log.info(
            "share_link_expired",
            share_link_id=str(share_link.id),
            expires_at=share_link.expires_at.isoformat(),
        )
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This sharing link has expired",
        )

    review = share_link.review
    if review.status != "complete":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shared review is unavailable",
        )

    return review, share_link
