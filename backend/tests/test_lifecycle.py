"""Lifecycle regressions: no paid model calls and no real workspace data."""
import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.config import settings
from app.models.library import AnalyzeRequest
from app.routers import files
from app.services import job_runner, media_probe
from app.services.job_store import (
    claim_analysis, claim_deletion, get_job, recover_interrupted_jobs, update_job,
)


def _local_files(asset):
    root = Path(settings.upload_dir)
    root.mkdir(parents=True, exist_ok=True)
    original = root / f'{asset.job_id}.mov'
    original.write_bytes(b'fake source for lifecycle tests')
    directory = root / asset.job_id
    (directory / 'thumbs').mkdir(parents=True)
    (directory / 'poster.jpg').write_bytes(b'poster')
    (directory / 'thumbs' / 'shot_1.jpg').write_bytes(b'thumbnail')
    update_job(asset.job_id, local_path=str(original))
    return original, directory


def test_analysis_and_deletion_claims_are_mutually_exclusive(asset):
    assert claim_analysis(asset.job_id)
    assert not claim_deletion(asset.job_id)
    update_job(asset.job_id, status='complete', analysis_history=[{'shot_annotations': {'1': {'notes': 'Preserved'}}}])
    assert claim_deletion(asset.job_id)
    assert get_job(asset.job_id).status == 'deleting'
    assert not claim_analysis(asset.job_id)
    assert not claim_deletion(asset.job_id)
    assert get_job(asset.job_id).analysis_history[0]['shot_annotations']['1']['notes'] == 'Preserved'


def test_delete_reserves_asset_during_remote_wait_and_removes_all_owned_media(client, asset, monkeypatch):
    original, directory = _local_files(asset)
    sibling = Path(settings.upload_dir) / 'other-asset'
    sibling.mkdir()
    (sibling / 'keep.jpg').write_bytes(b'keep')
    observed = []

    def remote_delete(*, name):
        observed.append((get_job(asset.job_id).status, claim_analysis(asset.job_id)))

    monkeypatch.setattr(files, 'get_client', lambda key: SimpleNamespace(files=SimpleNamespace(delete=remote_delete)))
    response = client.delete(f'/api/files/{asset.job_id}')
    assert response.status_code == 200
    assert observed == [('deleting', False)]
    assert response.json()['remote_deleted'] is True
    assert get_job(asset.job_id) is None
    assert not original.exists()
    assert not directory.exists()
    assert (sibling / 'keep.jpg').read_bytes() == b'keep'


def test_active_analysis_prevents_deletion_before_remote_or_local_work(client, asset, monkeypatch):
    original, directory = _local_files(asset)
    remote = Mock()
    monkeypatch.setattr(files, 'get_client', remote)
    assert claim_analysis(asset.job_id)
    assert client.delete(f'/api/files/{asset.job_id}').status_code == 409
    remote.assert_not_called()
    assert original.exists() and directory.exists()


def test_delete_keeps_local_cleanup_when_remote_cleanup_fails(client, asset, monkeypatch):
    original, directory = _local_files(asset)
    monkeypatch.setattr(files, 'get_client', Mock(side_effect=RuntimeError('unavailable')))
    result = client.delete(f'/api/files/{asset.job_id}')
    assert result.status_code == 200
    assert result.json()['remote_deleted'] is False
    assert get_job(asset.job_id) is None
    assert not original.exists() and not directory.exists()


def test_delete_rejects_paths_outside_workspace_before_any_deletion(client, asset, tmp_path, monkeypatch):
    outside = tmp_path / 'outside.mov'
    outside.write_bytes(b'keep')
    update_job(asset.job_id, local_path=str(outside))
    remote = Mock()
    monkeypatch.setattr(files, 'get_client', remote)
    response = client.delete(f'/api/files/{asset.job_id}')
    assert response.status_code == 409
    assert outside.read_bytes() == b'keep'
    assert get_job(asset.job_id).status == 'error'
    remote.assert_not_called()
    with pytest.raises(ValueError, match='directory'):
        files._deletion_paths(SimpleNamespace(job_id='..', local_path=''))
    with pytest.raises(ValueError, match='directory'):
        files._deletion_paths(SimpleNamespace(job_id='../neighbor', local_path=''))


def test_local_cleanup_failure_retains_record_for_retry(client, asset, monkeypatch):
    _, directory = _local_files(asset)
    update_job(asset.job_id, file_id='')
    monkeypatch.setattr(files.shutil, 'rmtree', Mock(side_effect=PermissionError('in use')))
    result = client.delete(f'/api/files/{asset.job_id}')
    assert result.status_code == 500
    assert get_job(asset.job_id).status == 'error'
    assert 'retry' in get_job(asset.job_id).progress.lower()
    assert directory.exists()


def test_interrupted_deletion_can_be_retried_after_restart(asset):
    assert claim_deletion(asset.job_id)
    recover_interrupted_jobs()
    recovered = get_job(asset.job_id)
    assert recovered.status == 'error'
    assert 'Retry deletion' in recovered.error
    assert claim_deletion(asset.job_id)


def test_immediate_cancel_updates_state_and_clears_task_even_before_coroutine_starts(asset, monkeypatch):
    upload = AsyncMock()
    monkeypatch.setattr(job_runner, 'ensure_remote_file', upload)
    assert claim_analysis(asset.job_id)

    async def scenario():
        job_runner.start_job(asset.job_id, AnalyzeRequest(), 'never-persist-this-key')
        task = job_runner._tasks[asset.job_id]
        assert job_runner.cancel_job(asset.job_id)
        await asyncio.gather(task, return_exceptions=True)
        assert task.cancelled()
        assert asset.job_id not in job_runner._tasks
        assert not job_runner.cancel_job(asset.job_id)

    asyncio.run(scenario())
    upload.assert_not_awaited()
    result = get_job(asset.job_id)
    assert result.status == 'error'
    assert result.progress == 'Cancelled'
    assert result.flash_result == asset.flash_result
    assert 'never-persist-this-key' not in str(result)


def test_cancel_waiting_for_semaphore_does_not_consume_capacity(asset, monkeypatch):
    upload = AsyncMock()
    monkeypatch.setattr(job_runner, 'ensure_remote_file', upload)
    assert claim_analysis(asset.job_id)

    async def scenario():
        gate = asyncio.Semaphore(0)
        job_runner._gate = gate
        try:
            job_runner.start_job(asset.job_id, AnalyzeRequest(), None)
            task = job_runner._tasks[asset.job_id]
            await asyncio.sleep(0)  # Let _run reach the capacity wait.
            assert job_runner.cancel_job(asset.job_id)
            await asyncio.gather(task, return_exceptions=True)
            gate.release()
            await asyncio.wait_for(gate.acquire(), timeout=1)
            assert asset.job_id not in job_runner._tasks
        finally:
            job_runner._gate = None

    asyncio.run(scenario())
    upload.assert_not_awaited()
    assert get_job(asset.job_id).progress == 'Cancelled'


def test_stale_completion_callback_cannot_remove_newer_task(asset):
    old_task, new_task = Mock(), Mock()
    job_runner._tasks[asset.job_id] = new_task
    try:
        job_runner._finished(asset.job_id, old_task)
        assert job_runner._tasks[asset.job_id] is new_task
        old_task.cancelled.assert_not_called()
    finally:
        job_runner._tasks.pop(asset.job_id, None)


def test_cancelled_probe_kills_and_waits_for_subprocess(monkeypatch):
    proc = SimpleNamespace(returncode=None, communicate=AsyncMock(side_effect=asyncio.CancelledError),
                           wait=AsyncMock(return_value=-9), kill=Mock())
    monkeypatch.setattr(media_probe.asyncio, 'create_subprocess_exec', AsyncMock(return_value=proc))
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(media_probe.probe_media('source.mov'))
    proc.kill.assert_called_once()
    proc.wait.assert_awaited_once()


def test_cancelled_poster_kills_and_waits_for_subprocess(tmp_path, monkeypatch):
    proc = SimpleNamespace(returncode=None, wait=AsyncMock(side_effect=[asyncio.CancelledError, -9]), kill=Mock())
    monkeypatch.setattr(media_probe.asyncio, 'create_subprocess_exec', AsyncMock(return_value=proc))
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(media_probe.create_poster('source.mov', str(tmp_path / 'poster.jpg'), 10))
    proc.kill.assert_called_once()
    assert proc.wait.await_count == 2
