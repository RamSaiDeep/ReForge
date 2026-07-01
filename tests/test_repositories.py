from datetime import datetime
import pytest
from reforge.adapters.repositories import InMemoryProjectRepository, JSONFileProjectRepository
from reforge.domain.models import ExcavationState, ExcavationStatus, RepositoryProfile

@pytest.fixture
def sample_state() -> ExcavationState:
    now = datetime.utcnow()
    profile = RepositoryProfile(
        url="https://github.com/test/repo",
        name="repo",
        owner="test",
        primary_language="Python",
        languages={"Python": 1.0},
        stars=100,
        forks=20,
        watchers=10,
        license="MIT",
        contributors_count=5,
        last_commit_at=now,
        created_at=now,
        readme_content="Simple test readme",
    )
    return ExcavationState(
        project_id="test-project",
        repository_url="https://github.com/test/repo",
        status=ExcavationStatus.DISCOVERED,
        profile=profile,
    )


@pytest.mark.asyncio
async def test_in_memory_repository(sample_state):
    repo = InMemoryProjectRepository()
    
    # Initially should be empty
    assert await repo.get_by_id("test-project") is None
    assert len(await repo.list_projects()) == 0

    # Save
    await repo.save(sample_state)
    
    # Retrieve
    retrieved = await repo.get_by_id("test-project")
    assert retrieved is not None
    assert retrieved.project_id == "test-project"
    assert retrieved.status == ExcavationStatus.DISCOVERED
    assert retrieved.profile.stars == 100
    
    # Verify copy isolation
    retrieved.status = ExcavationStatus.FAILED
    refetched = await repo.get_by_id("test-project")
    assert refetched.status == ExcavationStatus.DISCOVERED


@pytest.mark.asyncio
async def test_json_file_repository(sample_state, tmp_path):
    # Use pytest's tmp_path as storage directory
    repo = JSONFileProjectRepository(storage_dir=str(tmp_path))
    
    # Initially should be empty
    assert await repo.get_by_id("test-project") is None
    assert len(await repo.list_projects()) == 0

    # Save
    await repo.save(sample_state)
    
    # Check that file was created
    file_path = tmp_path / "test-project.json"
    assert file_path.exists()
    
    # Retrieve
    retrieved = await repo.get_by_id("test-project")
    assert retrieved is not None
    assert retrieved.project_id == "test-project"
    assert retrieved.profile.name == "repo"
    
    # List projects
    projects = await repo.list_projects()
    assert len(projects) == 1
    assert projects[0].project_id == "test-project"
