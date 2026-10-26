"""PID-lock regression tests (PID reuse after a machine restart)."""

import os

import pytest

import entry as entry_module
from app.config import settings


@pytest.fixture
def pid_file(tmp_path, monkeypatch):
    path = tmp_path / ".pa-backend.pid"
    monkeypatch.setattr(settings, "PID_FILE", path)
    return path


def test_no_lockfile_writes_current_pid(pid_file):
    entry_module.check_pid_lock()
    assert pid_file.read_text().strip() == str(os.getpid())


def test_dead_pid_is_reclaimed(pid_file):
    pid_file.write_text("999999999")
    entry_module.check_pid_lock()
    assert pid_file.read_text().strip() == str(os.getpid())


def test_recycled_live_pid_is_reclaimed(pid_file):
    """PID 1 is alive but is not Prompt Architect — simulates PID reuse
    after a machine restart (regression guard for the desktop launch bug)."""
    assert entry_module._looks_like_our_backend(1) is False
    pid_file.write_text("1")
    entry_module.check_pid_lock()
    assert pid_file.read_text().strip() == str(os.getpid())


def test_live_our_pid_blocks_startup(pid_file, monkeypatch):
    pid_file.write_text(str(os.getpid()))
    monkeypatch.setattr(entry_module, "_looks_like_our_backend", lambda pid: True)
    with pytest.raises(SystemExit):
        entry_module.check_pid_lock()


def test_garbage_pidfile_is_reclaimed(pid_file):
    pid_file.write_text("not-a-pid")
    entry_module.check_pid_lock()
    assert pid_file.read_text().strip() == str(os.getpid())
