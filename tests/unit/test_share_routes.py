"""Tests for share-related API routes."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from api.main import app
from api.middleware.auth import get_current_user
from api.schemas.review import PublicReviewSummary, ShareLinkResponse
from core.database import get_db
from core.models.user import User


@pytest.fixture
def mock_user():
    user = Mock(spec=User)
    user.id = str(uuid4())
    user.email = "owner@example.com"
    user.is_active = True
    return user


@pytest.fixture
def mock_db():
    session = AsyncMock()
    session.add = Mock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.mark.unit
class TestShareRoutes:
    """API-level tests for share link creation and public retrieval."""

    @pytest.mark.asyncio
    async def test_authenticated_user_can_create_share_link(self, mock_user, mock_db):
        """POST /reviews/{id}/share returns token and share path for owners."""
        review_id = uuid4()
        expires_at = datetime.now(UTC) + timedelta(days=30)
        share_link = Mock()
        share_link.token = "abc123securetoken"
        share_link.expires_at = expires_at

        async def override_user():
            return mock_user

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_current_user] = override_user
        app.dependency_overrides[get_db] = override_db

        try:
            with (
                patch(
                    "api.routes.reviews.create_share_link",
                    new_callable=AsyncMock,
                    return_value=share_link,
                ),
                patch("api.main.init_db", new_callable=AsyncMock),
            ):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.post(f"/reviews/{review_id}/share")

            assert response.status_code == 200
            data = response.json()
            assert data["token"] == "abc123securetoken"
            assert data["share_path"] == "/share/abc123securetoken"
            assert "expires_at" in data
            ShareLinkResponse.model_validate(data)
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_create_share_link_requires_authentication(self, mock_db):
        """Unauthenticated POST /reviews/{id}/share returns 401."""

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        try:
            with patch("api.main.init_db", new_callable=AsyncMock):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.post(f"/reviews/{uuid4()}/share")

            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_public_endpoint_returns_summary_without_auth(self, mock_db):
        """GET /share/{token} works without authentication and omits private fields."""
        review = Mock()
        review.status = "complete"
        review.overall_score = 0.81
        review.sections = [
            {
                "section_name": "Technical Skills",
                "content": "Solid fundamentals",
                "confidence": 0.85,
                "suggestions": ["Add more detail"],
            }
        ]
        review.id = str(uuid4())
        review.profile_id = str(uuid4())
        review.error_message = "secret-internal"

        share_link = Mock()
        share_link.expires_at = datetime.now(UTC) + timedelta(days=15)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        try:
            with (
                patch(
                    "api.routes.share.get_shared_review",
                    new_callable=AsyncMock,
                    return_value=(review, share_link),
                ),
                patch("api.main.init_db", new_callable=AsyncMock),
            ):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.get("/share/public-token")

            assert response.status_code == 200
            data = response.json()
            PublicReviewSummary.model_validate(data)
            assert data["status"] == "complete"
            assert data["overall_score"] == 0.81
            assert data["sections"][0]["section_name"] == "Technical Skills"
            assert "id" not in data
            assert "profile_id" not in data
            assert "error_message" not in data
            assert "user" not in data
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_public_endpoint_expired_token(self, mock_db):
        """GET /share/{token} returns 410 for expired links."""

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        try:
            with (
                patch(
                    "api.routes.share.get_shared_review",
                    new_callable=AsyncMock,
                    side_effect=HTTPException(
                        status_code=410, detail="This sharing link has expired"
                    ),
                ),
                patch("api.main.init_db", new_callable=AsyncMock),
            ):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.get("/share/expired-token")

            assert response.status_code == 410
            assert "expired" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_public_endpoint_invalid_token(self, mock_db):
        """GET /share/{token} returns 404 for invalid tokens."""

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        try:
            with (
                patch(
                    "api.routes.share.get_shared_review",
                    new_callable=AsyncMock,
                    side_effect=HTTPException(status_code=404, detail="Share link not found"),
                ),
                patch("api.main.init_db", new_callable=AsyncMock),
            ):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.get("/share/bad-token")

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_public_endpoint_is_read_only(self, mock_db):
        """Public share router exposes GET only; write verbs are rejected."""
        openapi_paths = app.openapi()["paths"]
        share_paths = {
            path: methods for path, methods in openapi_paths.items() if path.startswith("/share")
        }
        assert share_paths
        for path, methods in share_paths.items():
            assert set(methods.keys()) == {"get"}
            assert "{" in path

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        try:
            with patch("api.main.init_db", new_callable=AsyncMock):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    for method in ("post", "put", "patch", "delete"):
                        response = await getattr(client, method)("/share/some-token")
                        assert response.status_code == 405
        finally:
            app.dependency_overrides.clear()
