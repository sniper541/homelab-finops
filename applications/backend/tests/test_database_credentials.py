import json

import pytest

from app import database


def test_rotated_credentials_used_on_next_connection(tmp_path, monkeypatch):
    active = tmp_path / "database.json"
    monkeypatch.setenv("POSTGRES_CREDENTIALS_FILE", str(active))
    calls = []
    monkeypatch.setattr(database.psycopg, "connect", lambda **kwargs: calls.append(kwargs))
    for username in ("lease_one", "lease_two"):
        replacement = tmp_path / "replacement.json"
        replacement.write_text(json.dumps({"username": username, "password": "test-only"}))
        replacement.replace(active)
        database.get_connection()
    assert [call["user"] for call in calls] == ["lease_one", "lease_two"]


@pytest.mark.parametrize("content", [None, "invalid-sensitive-data", "{}", "[]",
                                      '{"username": "x", "password": null}'])
def test_bad_credentials_fail_closed_without_exposing_contents(tmp_path, monkeypatch, content):
    active = tmp_path / "database.json"
    if content is not None:
        active.write_text(content)
    monkeypatch.setenv("POSTGRES_CREDENTIALS_FILE", str(active))
    monkeypatch.setenv("POSTGRES_PASSWORD", "bootstrap-must-not-be-used")
    monkeypatch.setattr(database.psycopg, "connect", lambda **_: pytest.fail("Must fail closed"))
    with pytest.raises(RuntimeError, match="^Database credentials are unavailable$"):
        database.get_connection()
