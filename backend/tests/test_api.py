"""Integration tests for FastAPI endpoints using httpx AsyncClient."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db
from app.main import app
from app.models.database import Base
from app.services.refactorer import CodeRefactorer
from app.api.routes.reports import _calculate_wcag_score

# In-memory SQLite async engine for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_async_session = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db():
    """Test database session generator."""
    async with test_async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Override dependency in FastAPI app
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
async def prepare_database():
    """Create all tables before each test and drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_health_check_endpoint() -> None:
    """Verify /api/health returns 200 OK and expected status payload."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "services" in data


@pytest.mark.asyncio
async def test_root_endpoint() -> None:
    """Verify root endpoint returns application metadata."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "WebRevive AI" in data["name"]
        assert data["docs"] == "/api/docs"


@pytest.mark.asyncio
async def test_project_crud_lifecycle() -> None:
    """Test full Project CRUD cycle: create, read, update, list, and delete."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create project
        create_payload = {
            "name": "Acme Portal",
            "url": "https://acme.example.com",
            "description": "Customer dashboard portal",
        }
        create_resp = await client.post("/api/projects", json=create_payload)
        assert create_resp.status_code == 201
        created_data = create_resp.json()
        project_id = created_data["id"]
        assert created_data["name"] == "Acme Portal"

        # 2. List projects
        list_resp = await client.get("/api/projects")
        assert list_resp.status_code == 200
        projects = list_resp.json()
        assert len(projects) >= 1

        # 3. Get single project
        get_resp = await client.get(f"/api/projects/{project_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == project_id

        # 4. Update project
        update_payload = {"name": "Acme Portal Refactored"}
        put_resp = await client.put(f"/api/projects/{project_id}", json=update_payload)
        assert put_resp.status_code == 200
        assert put_resp.json()["name"] == "Acme Portal Refactored"

        # 5. Delete project
        del_resp = await client.delete(f"/api/projects/{project_id}")
        assert del_resp.status_code == 200

        # Verify not found
        get_del_resp = await client.get(f"/api/projects/{project_id}")
        assert get_del_resp.status_code == 404


def test_wcag_score_calculation() -> None:
    """Verify WCAG compliance scoring formula."""
    # Perfect score: 0 issues
    assert _calculate_wcag_score(0, 0, 0, 0) == 100.0

    # 1 critical (15) + 1 serious (8) = 23 penalty -> 77.0
    assert _calculate_wcag_score(1, 1, 0, 0) == 77.0

    # Massive violations bounded at 0.0
    assert _calculate_wcag_score(10, 10, 10, 10) == 0.0


def test_code_refactorer_diff() -> None:
    """Verify diff generator outputs valid unified diff format."""
    refactorer = CodeRefactorer()
    original = "<html>\n<body>\n<img src='logo.png'>\n</body>\n</html>"
    modified = "<html>\n<body>\n<img src='logo.png' alt='Logo'>\n</body>\n</html>"

    diff = refactorer.generate_diff(original, modified)
    assert "--- original" in diff
    assert "+++ refactored" in diff
    assert "+<img src='logo.png' alt='Logo'>" in diff
