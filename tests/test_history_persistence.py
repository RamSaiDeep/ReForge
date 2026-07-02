import pytest
from datetime import datetime, timedelta
from reforge.domain.models import ExcavationState, ExcavationStatus
from reforge.adapters.repositories import InMemoryProjectRepository, JSONFileProjectRepository

@pytest.mark.asyncio
async def test_in_memory_repository_history():
    repo = InMemoryProjectRepository()
    
    t1 = datetime.utcnow() - timedelta(minutes=10)
    t2 = datetime.utcnow()
    
    state1 = ExcavationState(
        project_id="test-proj",
        repository_url="https://github.com/test/repo",
        status=ExcavationStatus.PENDING,
        updated_at=t1
    )
    
    state2 = ExcavationState(
        project_id="test-proj",
        repository_url="https://github.com/test/repo",
        status=ExcavationStatus.COMPLETED,
        updated_at=t2
    )

    await repo.save(state1)
    await repo.save(state2)

    history = await repo.get_project_history("test-proj")
    assert len(history) == 2
    assert history[0].status == ExcavationStatus.PENDING
    assert history[1].status == ExcavationStatus.COMPLETED
    assert history[0].updated_at == t1
    assert history[1].updated_at == t2


@pytest.mark.asyncio
async def test_json_file_repository_history(tmp_path):
    repo = JSONFileProjectRepository(storage_dir=str(tmp_path))
    
    t1 = datetime(2026, 7, 2, 12, 0, 0)
    t2 = datetime(2026, 7, 2, 12, 5, 0)
    
    state1 = ExcavationState(
        project_id="file-proj",
        repository_url="https://github.com/test/repo",
        status=ExcavationStatus.PENDING,
        updated_at=t1
    )
    
    state2 = ExcavationState(
        project_id="file-proj",
        repository_url="https://github.com/test/repo",
        status=ExcavationStatus.COMPLETED,
        updated_at=t2
    )

    await repo.save(state1)
    await repo.save(state2)

    history = await repo.get_project_history("file-proj")
    assert len(history) == 2
    assert history[0].status == ExcavationStatus.PENDING
    assert history[1].status == ExcavationStatus.COMPLETED
    assert history[0].updated_at == t1
    assert history[1].updated_at == t2

    # Check list_projects doesn't list historical snapshots (only main files)
    all_projects = await repo.list_projects()
    assert len(all_projects) == 1
    assert all_projects[0].project_id == "file-proj"
