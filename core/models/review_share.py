"""Review share link model for public, expiring review summary URLs."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base

if TYPE_CHECKING:
    from core.models.review import Review


class ReviewShareLink(Base):
    """Cryptographically secure, time-limited token for sharing a review summary."""

    __tablename__ = "review_share_links"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    review_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    review: Mapped["Review"] = relationship("Review", back_populates="share_links")

    __table_args__ = (
        Index("ix_review_share_links_token", "token"),
        Index("ix_review_share_links_review_id", "review_id"),
        Index("ix_review_share_links_expires_at", "expires_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<ReviewShareLink(id={self.id}, review_id={self.review_id}, "
            f"expires_at={self.expires_at})>"
        )
