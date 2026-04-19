"""Tests for new ToolPlugin models and methods (batch / background / hooks / approval)."""

from __future__ import annotations

import pytest

from openagents.interfaces.tool import (
    BatchItem,
    BatchResult,
    JobHandle,
    JobStatus,
    ToolExecutionRequest,
)


def test_batch_item_auto_generates_item_id():
    item = BatchItem(params={"x": 1})
    assert item.item_id
    assert item.params == {"x": 1}


def test_batch_result_preserves_item_id():
    r = BatchResult(item_id="abc", success=True, data=42)
    assert r.item_id == "abc"
    assert r.success is True
    assert r.data == 42


def test_job_handle_requires_status():
    h = JobHandle(job_id="j1", tool_id="t", status="pending", created_at=1.0)
    assert h.status == "pending"
    with pytest.raises(Exception):
        JobHandle(job_id="j1", tool_id="t", status="bogus", created_at=1.0)


def test_job_status_optional_progress():
    s = JobStatus(job_id="j1", status="running")
    assert s.progress is None


def test_tool_execution_request_accepts_cancel_event():
    import asyncio
    ev = asyncio.Event()
    req = ToolExecutionRequest(tool_id="t", tool=None, cancel_event=ev)
    assert req.cancel_event is ev


def test_tool_execution_request_cancel_event_defaults_none():
    req = ToolExecutionRequest(tool_id="t", tool=None)
    assert req.cancel_event is None
