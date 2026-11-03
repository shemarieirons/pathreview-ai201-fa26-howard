"""Tests for share_service.py — public review share links."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from core.services.share_service import (
    SHARE_LINK_TTL_DAYS,
    create_share_link,
    get_shared_review,
)


@pytest.mark.unit
class TestCreateShareLink:
    """Tests for creating authenticated share links."""

    @pytest.fixture
    def mock_db(self):
        session = AsyncMock()
        session.add = Mock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_creates_share_link_for_completed_review(self, mock_db):
        """Authenticated owner can generate a share link for a complete review."""
        review_id = uuid4()
        user_id = uuid4()

        mock_review = Mock()
        mock_review.id = str(review_id)
        mock_review.status = "complete"

        with (
            patch(
                "core.services.share_service.get_review",
                new_callable=AsyncMock,
                return_value=mock_review,
            ),
            patch(
                "core.services.share_service._get_active_share_link",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("core.services.share_service.ReviewShareLink") as MockLink,
        ):
            instance = MockLink.return_value
            instance.token = "secure-token"
            instance.id = str(uuid4())
            instance.expires_at = datetime.now(UTC) + timedelta(days=30)

            result = await create_share_link(mock_db, review_id, user_id)

            MockLink.assert_called_once()
            call_kwargs = MockLink.call_args.kwargs
            assert "token" in call_kwargs
            assert call_kwargs["review_id"] == str(review_id)
            assert call_kwargs["expires_at"] - call_kwargs["created_at"] == timedelta(
                days=SHARE_LINK_TTL_DAYS
            )
            mock_db.add.assert_called_once_with(instance)
            mock_db.commit.assert_awaited()
            assert result is instance

    @pytest.mark.asyncio
    async def test_reuses_existing_valid_share_link(self, mock_db):
        """Repeated requests reuse an unexpired share link instead of creating another."""
        review_id = uuid4()
        user_id = uuid4()
        mock_review = Mock(id=str(review_id), status="complete")
        existing = Mock()
        existing.id = str(uuid4())
        existing.token = "existing-valid-token"
        existing.expires_at = datetime.now(UTC) + timedelta(days=20)

        with (
            patch(
                "core.services.share_service.get_review",
                new_callable=AsyncMock,
                return_value=mock_review,
            ),
            patch(
                "core.services.share_service._get_active_share_link",
                new_callable=AsyncMock,
                return_value=existing,
            ),
            patch("core.services.share_service.ReviewShareLink") as MockLink,
        ):
            result = await create_share_link(mock_db, review_id, user_id)

            assert result is existing
            MockLink.assert_not_called()
            mock_db.add.assert_not_called()
            mock_db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_creates_new_link_when_existing_is_expired(self, mock_db):
        """A new token is created when no unexpired share link remains."""
        review_id = uuid4()
        user_id = uuid4()
        mock_review = Mock(id=str(review_id), status="complete")

        with (
            patch(
                "core.services.share_service.get_review",
                new_callable=AsyncMock,
                return_value=mock_review,
            ),
            patch(
                "core.services.share_service._get_active_share_link",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("core.services.share_service.ReviewShareLink") as MockLink,
        ):
            instance = MockLink.return_value
            instance.id = str(uuid4())
            instance.expires_at = datetime.now(UTC) + timedelta(days=30)

            result = await create_share_link(mock_db, review_id, user_id)

            MockLink.assert_called_once()
            mock_db.add.assert_called_once_with(instance)
            assert result is instance

    @pytest.mark.asyncio
    async def test_token_is_unique_and_unpredictable(self, mock_db):
        """Newly generated tokens should be unique opaque strings, not sequential IDs."""
        review_id = uuid4()
        user_id = uuid4()
        mock_review = Mock(id=str(review_id), status="complete")
        tokens: list[str] = []

        with (
            patch(
                "core.services.share_service.get_review",
                new_callable=AsyncMock,
                return_value=mock_review,
            ),
            patch(
                "core.services.share_service._get_active_share_link",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            for _ in range(5):
                with patch("core.services.share_service.ReviewShareLink") as MockLink:
                    instance = MockLink.return_value
                    instance.id = str(uuid4())
                    instance.expires_at = datetime.now(UTC) + timedelta(days=30)

                    await create_share_link(mock_db, review_id, user_id)
                    token = MockLink.call_args.kwargs["token"]
                    tokens.append(token)

        assert len(set(tokens)) == 5
        for token in tokens:
            assert isinstance(token, str)
            assert len(token) >= 32
            assert str(review_id) not in token

    @pytest.mark.asyncio
    async def test_expiration_is_exactly_30_days(self, mock_db):
        """Share links expire exactly 30 days after generation."""
        review_id = uuid4()
        user_id = uuid4()
        mock_review = Mock(id=str(review_id), status="complete")
        fixed_now = datetime(2026, 11, 2, 12, 0, 0, tzinfo=UTC)

        with (
            patch(
                "core.services.share_service.get_review",
                new_callable=AsyncMock,
                return_value=mock_review,
            ),
            patch(
                "core.services.share_service._get_active_share_link",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("core.services.share_service._utcnow", return_value=fixed_now),
            patch("core.services.share_service.ReviewShareLink") as MockLink,
        ):
            MockLink.return_value.expires_at = fixed_now + timedelta(days=30)
            MockLink.return_value.id = str(uuid4())

            await create_share_link(mock_db, review_id, user_id)

            expires_at = MockLink.call_args.kwargs["expires_at"]
            created_at = MockLink.call_args.kwargs["created_at"]
            assert created_at == fixed_now
            assert expires_at == fixed_now + timedelta(days=30)

    @pytest.mark.asyncio
    async def test_missing_review_returns_404(self, mock_db):
        """Creating a share link for a missing/unowned review raises 404."""
        with (
            patch(
                "core.services.share_service.get_review",
                new_callable=AsyncMock,
                return_value=None,
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await create_share_link(mock_db, uuid4(), uuid4())

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_incomplete_review_cannot_be_shared(self, mock_db):
        """Only completed reviews can be shared."""
        mock_review = Mock(id=str(uuid4()), status="pending")

        with (
            patch(
                "core.services.share_service.get_review",
                new_callable=AsyncMock,
                return_value=mock_review,
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await create_share_link(mock_db, uuid4(), uuid4())

        assert exc_info.value.status_code == 400
        assert "completed" in exc_info.value.detail.lower()


@pytest.mark.unit
class TestGetSharedReview:
    """Tests for resolving public share tokens."""

    @pytest.fixture
    def mock_db(self):
        session = AsyncMock()
        session.execute = AsyncMock()
        return session

    def _mock_execute(self, mock_db, share_link):
        mock_result = Mock()
        mock_result.scalars.return_value.first.return_value = share_link
        mock_db.execute = AsyncMock(return_value=mock_result)

    @pytest.mark.asyncio
    async def test_valid_token_returns_review_without_auth(self, mock_db):
        """A valid unexpired token returns the associated review."""
        review = Mock()
        review.id = str(uuid4())
        review.status = "complete"
        review.overall_score = 0.85
        review.sections = [
            {
                "section_name": "Skills",
                "content": "Strong skills",
                "confidence": 0.9,
                "suggestions": ["Keep going"],
            }
        ]
        review.profile_id = str(uuid4())

        share_link = Mock()
        share_link.review = review
        share_link.expires_at = datetime.now(UTC) + timedelta(days=10)
        share_link.id = str(uuid4())

        self._mock_execute(mock_db, share_link)

        result_review, result_link = await get_shared_review(mock_db, "valid-token")

        assert result_review is review
        assert result_link is share_link
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_expired_token_returns_410(self, mock_db):
        """Expired tokens cannot retrieve the summary."""
        review = Mock(status="complete")
        share_link = Mock()
        share_link.review = review
        share_link.expires_at = datetime.now(UTC) - timedelta(days=1)
        share_link.id = str(uuid4())

        self._mock_execute(mock_db, share_link)

        with pytest.raises(HTTPException) as exc_info:
            await get_shared_review(mock_db, "expired-token")

        assert exc_info.value.status_code == 410
        assert "expired" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_invalid_token_returns_404(self, mock_db):
        """Unknown tokens return 404."""
        self._mock_execute(mock_db, None)

        with pytest.raises(HTTPException) as exc_info:
            await get_shared_review(mock_db, "missing-token")

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_empty_token_returns_404(self, mock_db):
        """Missing/blank tokens return 404."""
        with pytest.raises(HTTPException) as exc_info:
            await get_shared_review(mock_db, "   ")

        assert exc_info.value.status_code == 404
        mock_db.execute.assert_not_called()


@pytest.mark.unit
class TestPublicSummaryPrivacy:
    """Ensure public payloads do not expose private fields."""

    def test_public_schema_excludes_private_fields(self):
        """PublicReviewSummary should only expose summary display fields."""
        from api.schemas.review import PublicReviewSummary

        fields = set(PublicReviewSummary.model_fields.keys())
        assert fields == {"status", "overall_score", "sections", "expires_at"}
        assert "id" not in fields
        assert "profile_id" not in fields
        assert "error_message" not in fields
        assert "user_id" not in fields
        assert "created_at" not in fields

    def test_public_summary_serialization_omits_identifiers(self):
        """Serialized public summary must not include review/user identifiers."""
        from api.schemas.review import FeedbackSection, PublicReviewSummary

        summary = PublicReviewSummary(
            status="complete",
            overall_score=0.8,
            sections=[
                FeedbackSection(
                    section_name="Skills",
                    content="Good",
                    confidence=0.9,
                    suggestions=["Add metrics"],
                )
            ],
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
        payload = summary.model_dump()
        assert "id" not in payload
        assert "profile_id" not in payload
        assert payload["status"] == "complete"
        assert payload["overall_score"] == 0.8
